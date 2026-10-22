# Adapted from ModelScope 1.40.2 / Pytorch_Retinaface; see ../NOTICE.txt.
import json
import cv2
import numpy as np
import torch
from .models.retinaface import RetinaFace
from .utils import PriorBox, decode, decode_landm, py_cpu_nms

class RetinaFaceDetection:
    def __init__(self, model_path, config_path, device):
        self.cfg=json.loads(config_path.read_text(encoding='utf-8'))['models']
        if self.cfg.get('name')!='Resnet50':
            raise ValueError('人脸检测配置不是已验证的Resnet50。')
        self.cfg['pretrain']=False
        self.net=RetinaFace(cfg=self.cfg)
        state=torch.load(str(model_path),map_location='cpu',weights_only=True)
        state=state.get('state_dict',state)
        state={k.removeprefix('module.'):v for k,v in state.items()}
        self.net.load_state_dict(state,strict=True)
        self.net.eval().to(device)
        self.device=device

    def forward(self, input):
        img_raw = input['img'].cpu().numpy()
        img = np.float32(img_raw)

        im_height, im_width = img.shape[:2]
        ss = 1.0
        # tricky
        if max(im_height, im_width) > 1500:
            ss = 1000.0 / max(im_height, im_width)
            img = cv2.resize(img, (0, 0), fx=ss, fy=ss)
            im_height, im_width = img.shape[:2]

        scale = torch.Tensor(
            [img.shape[1], img.shape[0], img.shape[1], img.shape[0]])
        img -= (104, 117, 123)
        img = img.transpose(2, 0, 1)
        img = torch.from_numpy(img).unsqueeze(0)
        img = img.to(self.device)
        scale = scale.to(self.device)

        loc, conf, landms = self.net(img)  # forward pass
        del img

        confidence_threshold = 0.9
        nms_threshold = 0.4
        top_k = 5000
        keep_top_k = 750

        priorbox = PriorBox(self.cfg, image_size=(im_height, im_width))
        priors = priorbox.forward()
        priors = priors.to(self.device)
        prior_data = priors.data
        boxes = decode(loc.data.squeeze(0), prior_data, self.cfg['variance'])
        boxes = boxes * scale
        boxes = boxes.cpu().numpy()
        scores = conf.squeeze(0).data.cpu().numpy()[:, 1]
        landms = decode_landm(
            landms.data.squeeze(0), prior_data, self.cfg['variance'])
        scale1 = torch.Tensor([
            im_width, im_height, im_width, im_height, im_width, im_height,
            im_width, im_height, im_width, im_height
        ])
        scale1 = scale1.to(self.device)
        landms = landms * scale1
        landms = landms.cpu().numpy()

        # ignore low scores
        inds = np.where(scores > confidence_threshold)[0]
        boxes = boxes[inds]
        landms = landms[inds]
        scores = scores[inds]

        # keep top-K before NMS
        order = scores.argsort()[::-1][:top_k]
        boxes = boxes[order]
        landms = landms[order]
        scores = scores[order]

        # do NMS
        dets = np.hstack((boxes, scores[:, np.newaxis])).astype(
            np.float32, copy=False)
        keep = py_cpu_nms(dets, nms_threshold)
        dets = dets[keep, :]
        landms = landms[keep]

        # keep top-K faster NMS
        dets = dets[:keep_top_k, :]
        landms = landms[:keep_top_k, :]

        landms = landms.reshape((-1, 5, 2))
        landms = landms.reshape(
            -1,
            10,
        )
        return dets / ss, landms / ss

