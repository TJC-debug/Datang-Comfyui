# Adapted from ModelScope 1.40.2; the returned MASK is the actual local detector output.
import torch
import torch.nn.functional as F
from .utils import patch_partition_overlap,patch_aggregation_overlap,smooth_border_mg

class RetouchMethods:
    def retouch_local(self, image):
        """
        image: rgb
        """
        with torch.no_grad():
            sub_H, sub_W = image.shape[2:]

            sub_image_standard = F.interpolate(
                image, size=(768, 768), mode='bilinear', align_corners=True)
            sub_mask_pred = torch.sigmoid(
                self.detection_net(sub_image_standard))
            sub_mask_pred = F.interpolate(
                sub_mask_pred, size=(sub_H, sub_W), mode='nearest')

            sub_mask_pred_hard_low = (sub_mask_pred >= 0.35).float()
            sub_mask_pred_hard_high = (sub_mask_pred >= 0.5).float()
            sub_mask_pred = sub_mask_pred * (
                1 - sub_mask_pred_hard_high) + sub_mask_pred_hard_high
            sub_mask_pred = sub_mask_pred * sub_mask_pred_hard_low
            sub_mask_pred = 1 - sub_mask_pred

            sub_H_standard = sub_H if sub_H % self.patch_size == 0 else (
                sub_H // self.patch_size + 1) * self.patch_size
            sub_W_standard = sub_W if sub_W % self.patch_size == 0 else (
                sub_W // self.patch_size + 1) * self.patch_size

            sub_image_padding = F.pad(
                image,
                pad=(0, sub_W_standard - sub_W, 0, sub_H_standard - sub_H, 0,
                     0),
                mode='constant',
                value=0)
            sub_mask_pred_padding = F.pad(
                sub_mask_pred,
                pad=(0, sub_W_standard - sub_W, 0, sub_H_standard - sub_H, 0,
                     0),
                mode='constant',
                value=0)

            sub_image_padding = patch_partition_overlap(
                sub_image_padding, p1=self.patch_size, p2=self.patch_size)
            sub_mask_pred_padding = patch_partition_overlap(
                sub_mask_pred_padding, p1=self.patch_size, p2=self.patch_size)
            B_padding, C_padding, _, _ = sub_image_padding.size()

            sub_comp_padding_list = []
            for window_item in range(B_padding):
                sub_image_padding_window = sub_image_padding[
                    window_item:window_item + 1]
                sub_mask_pred_padding_window = sub_mask_pred_padding[
                    window_item:window_item + 1]

                sub_input_image_padding_window = sub_image_padding_window * sub_mask_pred_padding_window

                sub_output_padding_window = self.inpainting_net(
                    sub_input_image_padding_window,
                    sub_mask_pred_padding_window)
                sub_comp_padding_window = sub_input_image_padding_window + (
                    1
                    - sub_mask_pred_padding_window) * sub_output_padding_window

                sub_comp_padding_list.append(sub_comp_padding_window)

            sub_comp_padding = torch.cat(sub_comp_padding_list, dim=0)
            sub_comp = patch_aggregation_overlap(
                sub_comp_padding,
                h=int(round(sub_H_standard / self.patch_size)),
                w=int(round(sub_W_standard
                            / self.patch_size)))[:, :, :sub_H, :sub_W]

            return sub_comp, 1 - sub_mask_pred


    def predict_roi(self,
                    roi,
                    degree=1.0,
                    smooth_border=False,
                    return_mg=False):
        with torch.no_grad():
            image = F.interpolate(
                roi, (self.input_size, self.input_size), mode='bilinear')

            pred_mg = self.generator(image)  # value: 0~1
            pred_mg = (pred_mg - 0.5) * degree + 0.5
            pred_mg = pred_mg.clamp(0.0, 1.0)
            pred_mg = F.interpolate(pred_mg, roi.shape[2:], mode='bilinear')
            pred_mg = pred_mg[0].permute(
                1, 2, 0)  # ndarray, (h, w, 1) or (h0, w0, 3)
            if len(pred_mg.shape) == 2:
                pred_mg = pred_mg[..., None]

            if smooth_border:
                pred_mg = smooth_border_mg(self.diffuse_mask, pred_mg)

            image = (roi[0].permute(1, 2, 0) + 1.0) / 2

            pred = (1 - 2 * pred_mg
                    ) * image * image + 2 * pred_mg * image  # value: 0~1

            pred = (pred * 255.0).byte()  # ndarray, (h, w, 3), rgb

            output = {'pred': pred}
            if return_mg:
                output['pred_mg'] = pred_mg.cpu().numpy()
            return output

