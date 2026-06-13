import pytest
from myvoiceclone.jobs.queue import JobQueue
from myvoiceclone.jobs.runner import JobRunner
from myvoiceclone.adapters.audio.ffmpeg import FFmpegAdapter
from myvoiceclone.adapters.diarization.pyannote_adapter import PyannoteAdapter
from myvoiceclone.adapters.separation.demucs_adapter import DemucsAdapter
from myvoiceclone.adapters.asr.whisper_adapter import WhisperAdapter
from myvoiceclone.storage.repositories import JobRepository, SegmentRepository

@pytest.mark.unit
def test_job_runner_success_preprocess(db_conn, artifact_store, synthetic_wav):
    queue = JobQueue(db_conn)
    job = queue.enqueue("preprocess_all", {"filepath": synthetic_wav})
    
    assert job.status == "pending"
    
    runner = JobRunner(
        conn=db_conn,
        artifact_store=artifact_store,
        ffmpeg_adapter=FFmpegAdapter(),
        pyannote_adapter=PyannoteAdapter(),
        demucs_adapter=DemucsAdapter(),
        whisper_adapter=WhisperAdapter()
    )
    
    runner.run(job.id)
    
    job_repo = JobRepository(db_conn)
    job_after = job_repo.get_by_id(job.id)
    assert job_after.status == "completed"
    assert job_after.error_msg is None
    
    # Check that events were written
    events = job_repo.get_events(job.id)
    assert len(events) >= 3  # enqueue, start, complete
    assert events[1].status_to == "running"
    assert events[2].status_to == "completed"
    
    # Check that segments were created and scored
    seg_repo = SegmentRepository(db_conn)
    cursor = db_conn.cursor()
    cursor.execute("SELECT id FROM recordings;")
    rec_id = cursor.fetchone()[0]
    segments = seg_repo.list_by_recording(rec_id)
    assert len(segments) == 2
    assert all(s.status == "processed" for s in segments)

@pytest.mark.unit
def test_job_runner_failure(db_conn, artifact_store):
    queue = JobQueue(db_conn)
    # File does not exist, should fail
    job = queue.enqueue("preprocess_all", {"filepath": "/tmp/nonexistent.wav"})
    
    runner = JobRunner(
        conn=db_conn,
        artifact_store=artifact_store,
        ffmpeg_adapter=FFmpegAdapter(),
        pyannote_adapter=PyannoteAdapter(),
        demucs_adapter=DemucsAdapter(),
        whisper_adapter=WhisperAdapter()
    )
    
    with pytest.raises(Exception):
        runner.run(job.id)
        
    job_repo = JobRepository(db_conn)
    job_after = job_repo.get_by_id(job.id)
    assert job_after.status == "failed"
    assert "Source file not found" in job_after.error_msg
    
    events = job_repo.get_events(job.id)
    assert events[-1].status_to == "failed"
