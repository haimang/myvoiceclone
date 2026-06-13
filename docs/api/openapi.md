# OpenAPI Schema Snapshot for myvoiceclone API

This document provides a static snapshot of the HTTP REST API endpoints available in the engineering workbench.

## Endpoints

### recordings
* **GET** `/api/recordings`
  * Summary: List all recordings
  * Response: `List[RecordingResponse]`
* **GET** `/api/recordings/{recording_id}`
  * Summary: Get a recording by ID
  * Response: `RecordingResponse`
* **POST** `/api/recordings?filepath=...`
  * Summary: Submit an ingest job for a recording path
  * Response: `JobResponse`

### segments
* **GET** `/api/segments?recording_id=...`
  * Summary: Get segments belonging to a recording
  * Response: `List[SegmentResponse]`
* **GET** `/api/segments/{segment_id}`
  * Summary: Get a segment by ID
  * Response: `SegmentResponse`
* **PATCH** `/api/segments/{segment_id}/review`
  * Summary: Update segment review status and log transition
  * Body: `SegmentReviewUpdate`
  * Response: `SegmentResponse`

### datasets
* **GET** `/api/datasets`
  * Summary: List all datasets
  * Response: `List[DatasetResponse]`
* **GET** `/api/datasets/{dataset_id}`
  * Summary: Get dataset details
  * Response: `DatasetResponse`
* **POST** `/api/datasets`
  * Summary: Create an active dataset based on quality filters
  * Body: `DatasetCreate`
  * Response: `DatasetResponse`
* **POST** `/api/datasets/{dataset_id}/freeze`
  * Summary: Split, balance, and freeze dataset manifest checksum
  * Response: `DatasetResponse`

### jobs
* **GET** `/api/jobs`
  * Summary: List all jobs
  * Response: `List[JobResponse]`
* **GET** `/api/jobs/{job_id}`
  * Summary: Get job status and logs
  * Response: `JobResponse`
* **POST** `/api/jobs/{job_id}/run`
  * Summary: Manually execute a job synchronously using JobRunner
  * Response: `JobResponse`

### training
* **GET** `/api/training/runs`
  * Summary: List all model training runs
  * Response: `List[ModelRunResponse]`
* **GET** `/api/training/runs/{run_id}`
  * Summary: Get a model run by ID
  * Response: `ModelRunResponse`
* **POST** `/api/training/jobs`
  * Summary: Create a new train_sovits job
  * Body: `TrainJobCreate`
  * Response: `JobResponse`

### inference
* **POST** `/api/inference`
  * Summary: Perform voice conversion or XTTS synthesis
  * Body: `InferenceRequest`
  * Response: `ModelRunResponse`

### reports & audit
* **GET** `/api/reports`
  * Summary: List all evaluation reports
  * Response: `List[ReportResponse]`
* **GET** `/api/reports/{report_id}`
  * Summary: Get report details
  * Response: `ReportResponse`
* **POST** `/api/reports/baseline`
  * Summary: Generate baseline evaluation report
  * Body: `BaselineReportCreate`
  * Response: `ReportResponse`
* **POST** `/api/reports/train`
  * Summary: Generate long-train training report
  * Body: `TrainReportCreate`
  * Response: `ReportResponse`
* **POST** `/api/reports/gate`
  * Summary: Check long-train entrance binary gate
  * Body: `GateReportCreate`
  * Response: `dict` (Gate results)
* **GET** `/api/audit/trace?subject_id=...&subject_type=...`
  * Summary: Query cross-entity trace graph chronologically
  * Response: `dict`
