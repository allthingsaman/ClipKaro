# Models

`face_detection_yunet_2023mar.onnx` is the YuNet face detector from the
[OpenCV Model Zoo](https://github.com/opencv/opencv_zoo/tree/main/models/face_detection_yunet),
released under the MIT License. It's used to keep the speaker centred when reframing to 9:16.

For podcasts with two people on screen, ClipKaro also downloads three small models on first use
(about 50 MB, kept in `~/.cache/clipkaro/models`, not in this folder): pyannote segmentation 3.0
(MIT) and 3D-Speaker ERes2Net (Apache 2.0) to hear who is talking, and YAMNet (Apache 2.0) to hear
laughter. See `clipper/speakers.py`.
