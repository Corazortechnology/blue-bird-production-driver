# Model files

| File | Used by | How to obtain |
|------|---------|----------------|
| **`face_landmarker.task`** | MediaPipe `FaceDetector` | **Required** for face landmarks. [Download](https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task) — `Dockerfile.full` fetches this automatically. |
| **`arcface.onnx`** | ArcFace embeddings (`ArcFaceModel`) | If you see **`INVALID_PROTOBUF`** in logs, the file is probably a **Git LFS pointer** (tiny text file), not a real ONNX. Use **`git lfs pull`**, or download **`w600k_r50.onnx`** from InsightFace [buffalo_l](https://github.com/deepinsight/insightface/releases/download/v0.7/buffalo_l.zip) and save as `models/arcface.onnx`. **`Dockerfile.full`** replaces the pointer with that model during image build. |

### Local setup (one-time)

From project root:

```bash
mkdir -p models
curl -fsSL -o models/face_landmarker.task \
  "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task"
```

`Dockerfile.full` downloads this automatically for Kubernetes images.
