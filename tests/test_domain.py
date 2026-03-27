import pytest
from src.meridian.domain.entities import Chunk, ResearchJob, JobStatus, ResearchReport


def test_chunk_defaults_to_neutral_credibility():
    chunk = Chunk(document_id="doc123", content="Example chunk")
    assert chunk.credibility_score == 0.5

def test_research_job_initialization():
    job = ResearchJob(query="Quantum computing advances", status=JobStatus.PENDING)
    assert job.id is not None
    assert job.query == "Quantum computing advances"
    assert job.status == JobStatus.PENDING

def test_research_job_state_transitions():
    job = ResearchJob(query="Test", status=JobStatus.PENDING)
    
    # Start
    started_job = job.start()
    assert started_job.status == JobStatus.RUNNING
    assert started_job.id == job.id
    
    # Complete
    completed_job = started_job.complete()
    assert completed_job.status == JobStatus.COMPLETED
    assert completed_job.id == started_job.id
    
    # Fail
    failed_job = started_job.fail(error_message="Connection timeout")
    assert failed_job.status == JobStatus.FAILED
    assert failed_job.error_message == "Connection timeout"

def test_research_report_creation():
    report = ResearchReport(job_id="job123", query="Test", markdown_content="# Report")
    assert report.id is not None
    assert report.job_id == "job123"
    assert report.markdown_content == "# Report"
