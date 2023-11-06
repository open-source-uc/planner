import pytest
from app.sync.siding.client import AcademicPeriod
from pydantic import BaseModel, ValidationError


class AcademicPeriodTest(BaseModel):
    academic_period: AcademicPeriod


def test_academic_period():
    AcademicPeriodTest(academic_period=AcademicPeriod("2021-1"))
    AcademicPeriodTest(academic_period=AcademicPeriod("2023-2"))
    AcademicPeriodTest(academic_period=AcademicPeriod("2025-3"))

    with pytest.raises(ValidationError):
        AcademicPeriodTest(academic_period=AcademicPeriod("2021-0"))

    with pytest.raises(ValidationError):
        AcademicPeriodTest(academic_period=AcademicPeriod("2021-4"))

    with pytest.raises(ValidationError):
        AcademicPeriodTest(academic_period=AcademicPeriod("2021-5"))

    with pytest.raises(ValidationError):
        AcademicPeriodTest(academic_period=AcademicPeriod("KDSFDF"))

    with pytest.raises(ValidationError):
        AcademicPeriodTest(academic_period=AcademicPeriod(None))

    # Test deserialization from a dict with str
    d = {
        "academic_period": "2021-1",
    }
    apt = AcademicPeriodTest.model_validate(d)
    assert str(apt.academic_period) == "2021-1"
