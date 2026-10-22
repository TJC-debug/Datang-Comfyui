from pathlib import Path
from unittest import mock
import contextlib
import importlib.util
import sys
import unittest
import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]

def load_module():
    spec = importlib.util.spec_from_file_location("blemish_retouch_new", ROOT / "blemish_retouch.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

class FakeBackend:
    def __init__(self, faces=1, error=None):
        self.calls=[];self.faces=faces;self.error=error
    def run(self,rgb,local,texture):
        self.calls.append((rgb.copy(),local,texture))
        if self.error: raise self.error
        mask=np.zeros(rgb.shape[:2],np.float32);mask[2:5,3:6]=0.6
        return np.clip(rgb.astype(float)+40,0,255).astype(np.uint8),mask,self.faces

class BlemishRetouchTests(unittest.TestCase):
    def setUp(self):
        self.module=load_module();self.node=self.module.DatangBlemishRetouch();self.backend=FakeBackend()
        @contextlib.contextmanager
        def acquire(): yield self.backend
        self.engine=mock.Mock(acquire=acquire)
        self.patch=mock.patch.object(self.module,"_engine",return_value=self.engine)
        self.patch.start();self.addCleanup(self.patch.stop)
        self.image=torch.full((1,12,14,3),0.315,dtype=torch.float32)

    def test_stable_identity_ports_and_only_effective_controls(self):
        contract=self.node.INPUT_TYPES()
        self.assertEqual(list(contract["required"]),["图像"])
        self.assertEqual(list(contract["optional"]),["皮肤遮罩","祛痘修补","肤质强度","修复强度"])
        self.assertEqual(contract["optional"]["皮肤遮罩"],("MASK",))
        self.assertEqual(self.node.RETURN_TYPES,("IMAGE","MASK"))
        self.assertEqual(self.module.NODE_DISPLAY_NAME_MAPPINGS,{"DatangBlemishRetouch":"大汤人像痘印精修"})

    def test_single_image_without_mask_runs_model_and_returns_real_detector_mask(self):
        result,mask=self.node.retouch(self.image)
        self.assertEqual(len(self.backend.calls),1);self.assertTrue(self.backend.calls[0][1]);self.assertEqual(self.backend.calls[0][2],0.35)
        self.assertGreater(float(result.mean()),float(self.image.mean()));self.assertEqual(tuple(mask.shape),(1,12,14))
        self.assertAlmostEqual(float(mask[0,3,4]),0.6,places=6);self.assertEqual(float(mask[0,0,0]),0)
        self.assertLess(int(torch.count_nonzero(mask)),12*14)

    def test_zero_strength_bypasses_model_and_returns_exact_input(self):
        result,mask=self.node.retouch(self.image,修复强度=0)
        self.assertIs(result,self.image);self.assertEqual(len(self.backend.calls),0);self.assertFalse(torch.any(mask))

    def test_black_mask_bypasses_model(self):
        result,mask=self.node.retouch(self.image,torch.zeros((1,12,14)))
        self.assertIs(result,self.image);self.assertFalse(torch.any(mask));self.assertEqual(len(self.backend.calls),0)

    def test_all_effects_disabled_bypass_model(self):
        result,_=self.node.retouch(self.image,祛痘修补=False,肤质强度=0)
        self.assertIs(result,self.image);self.assertEqual(len(self.backend.calls),0)

    def test_external_mask_and_alpha_are_exact_hard_boundaries(self):
        image=torch.cat([self.image,torch.rand((1,12,14,1))],dim=-1);mask=torch.zeros((12,14));mask[:,7:]=1
        result,detected=self.node.retouch(image,mask,修复强度=100)
        self.assertTrue(torch.equal(result[:,:,:7],image[:,:,:7]));self.assertTrue(torch.equal(result[...,3],image[...,3]));self.assertFalse(torch.any(detected[:,:,:7]))
        self.assertGreater(float(result[:,:,7:,:3].mean()),float(image[:,:,7:,:3].mean()))

    def test_soft_mask_and_overall_strength_are_actual_blend_weights(self):
        full,_=self.node.retouch(self.image,修复强度=100);partial,_=self.node.retouch(self.image,torch.full((1,12,14),0.5),修复强度=50)
        self.assertTrue(torch.allclose(partial,self.image+(full-self.image)*0.25))

    def test_controls_forward_to_real_backend_parameters(self):
        self.node.retouch(self.image,祛痘修补=False,肤质强度=0.7)
        self.assertEqual(self.backend.calls[0][1:],(False,0.7))

    def test_old_api_names_are_accepted_without_reinterpreting_them(self):
        self.node.retouch(self.image,修复强度=85,检测灵敏度=58,最大瑕疵尺寸=36,深色斑点修复=85,红印修复=70,五官边缘保护=78,边缘羽化=6)
        self.assertEqual(self.backend.calls[0][1:],(True,0.35))

    def test_legacy_mask_batch_broadcast_and_resize_are_preserved(self):
        images=self.image.expand(2,-1,-1,-1).clone();mask=torch.zeros((1,6,7));mask[:,:,4:]=1
        output,detected=self.node.retouch(images,mask)
        self.assertEqual(tuple(output.shape),tuple(images.shape));self.assertEqual(tuple(detected.shape),(2,12,14));self.assertEqual(len(self.backend.calls),2)
        self.assertTrue(torch.equal(output[:,:,:5],images[:,:,:5]))

    def test_black_frame_in_batch_does_not_execute_model(self):
        images=self.image.expand(2,-1,-1,-1).clone();masks=torch.ones((2,12,14));masks[0]=0
        output,detected=self.node.retouch(images,masks)
        self.assertEqual(len(self.backend.calls),1);self.assertTrue(torch.equal(output[0],images[0]));self.assertFalse(torch.any(detected[0]))

    def test_invalid_mask_batch_and_nan_are_explicit(self):
        with self.assertRaises(ValueError):self.node.retouch(self.image,torch.ones((2,12,14)))
        with self.assertRaises(ValueError):self.node.retouch(self.image,torch.full((1,12,14),float('nan')))

    def test_invalid_new_control_values_do_not_masquerade_as_legacy_values(self):
        for kwargs in ({"肤质强度":58},{"肤质强度":float('nan')},{"修复强度":-1},{"祛痘修补":85}):
            with self.subTest(kwargs=kwargs),self.assertRaises(ValueError):self.node.retouch(self.image,**kwargs)

    def test_no_face_is_explicit_instead_of_fake_success(self):
        self.backend.faces=0
        with self.assertRaisesRegex(ValueError,"未检测到人脸"):self.node.retouch(self.image)

    def test_missing_model_and_oom_do_not_return_original_as_success(self):
        self.backend.error=FileNotFoundError("模型缺失")
        with self.assertRaises(FileNotFoundError):self.node.retouch(self.image)
        self.backend.error=torch.cuda.OutOfMemoryError("QA OOM")
        with self.assertRaisesRegex(RuntimeError,"显存不足"):self.node.retouch(self.image)

    def test_invalid_backend_dimensions_are_rejected(self):
        self.backend.run=lambda *a,**k:(np.zeros((1,1,3),np.uint8),np.zeros((1,1)),1)
        with self.assertRaisesRegex(RuntimeError,"无效图像"):self.node.retouch(self.image)

    def test_dependency_absence_does_not_break_whole_package_registration(self):
        name="datang_registration_no_skin_dependencies"
        with mock.patch.dict(sys.modules,{"torchvision":None,"tensorflow":None,"modelscope":None}):
            spec=importlib.util.spec_from_file_location(name,ROOT/"__init__.py",submodule_search_locations=[str(ROOT)])
            package=importlib.util.module_from_spec(spec);sys.modules[name]=package;spec.loader.exec_module(package)
        self.assertIn("DatangBlemishRetouch",package.NODE_CLASS_MAPPINGS)
        self.assertNotIn("NabeiModelScopeSkinRetouch",package.NODE_CLASS_MAPPINGS)
        self.assertIn("DatangFastFaceBeauty",package.NODE_CLASS_MAPPINGS)

if __name__=="__main__":unittest.main()