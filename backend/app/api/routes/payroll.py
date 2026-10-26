from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import PlainTextResponse, Response
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser, require_admin, require_admin_or_hr, require_any, require_hr
from app.core.database import get_db
from app.models.employee import Employee
from app.models.payroll import PayrollRun, Payslip
from app.schemas.payroll import PayrollRunCreate, PayrollRunOut, PayslipOut
from app.services import export_service, org_service, payroll_service
from app.services.payslip_pdf import render_payslip_pdf

router = APIRouter(prefix="/payroll", tags=["payroll"])


@router.post("/runs", response_model=PayrollRunOut)
def create_draft(payload: PayrollRunCreate, current: CurrentUser = Depends(require_hr), db: Session = Depends(get_db)):
    settings = org_service.get_settings(db)
    return payroll_service.create_or_refresh_draft(db, current.id, settings, payload.month, payload.year)


@router.get("/runs", response_model=list[PayrollRunOut])
def list_runs(current: CurrentUser = Depends(require_admin_or_hr), db: Session = Depends(get_db)):
    return db.query(PayrollRun).order_by(PayrollRun.year.desc(), PayrollRun.month.desc()).all()


@router.get("/runs/{run_id}", response_model=PayrollRunOut)
def get_run(run_id: int, current: CurrentUser = Depends(require_admin_or_hr), db: Session = Depends(get_db)):
    run = db.get(PayrollRun, run_id)
    if run is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Payroll run not found")
    return run


@router.get("/runs/{run_id}/export-csv", response_class=PlainTextResponse)
def export_run_csv(
    run_id: int,
    department_id: int | None = None,
    current: CurrentUser = Depends(require_admin_or_hr),
    db: Session = Depends(get_db),
):
    run = db.get(PayrollRun, run_id)
    if run is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Payroll run not found")

    query = db.query(Payslip).join(Employee, Payslip.employee_id == Employee.id).filter(Payslip.payroll_run_id == run_id)
    if department_id:
        query = query.filter(Employee.department_id == department_id)
    return export_service.payroll_csv(run, query.order_by(Employee.full_name).all())


@router.post("/runs/{run_id}/finalize", response_model=PayrollRunOut)
def finalize(run_id: int, current: CurrentUser = Depends(require_admin), db: Session = Depends(get_db)):
    run = db.get(PayrollRun, run_id)
    if run is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Payroll run not found")
    return payroll_service.finalize_run(db, current.id, run)


@router.get("/payslips", response_model=list[PayslipOut])
def payslips_for_employee(
    employee_id: int,
    current: CurrentUser = Depends(require_admin_or_hr),
    db: Session = Depends(get_db),
):
    return (
        db.query(Payslip)
        .join(PayrollRun)
        .filter(Payslip.employee_id == employee_id, PayrollRun.status == "finalized")
        .order_by(PayrollRun.year.desc(), PayrollRun.month.desc())
        .all()
    )


@router.get("/payslips/mine", response_model=list[PayslipOut])
def my_payslips(year: int | None = None, current: CurrentUser = Depends(require_any), db: Session = Depends(get_db)):
    if not current.employee_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "No employee profile for this account")
    query = (
        db.query(Payslip)
        .join(PayrollRun)
        .filter(Payslip.employee_id == current.employee_id, PayrollRun.status == "finalized")
    )
    if year:
        query = query.filter(PayrollRun.year == year)
    return query.order_by(PayrollRun.year.desc(), PayrollRun.month.desc()).all()


@router.get("/payslips/{payslip_id}/pdf")
def payslip_pdf(payslip_id: int, current: CurrentUser = Depends(require_any), db: Session = Depends(get_db)):
    slip = db.get(Payslip, payslip_id)
    if slip is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Payslip not found")
    if current.role == "employee" and slip.employee_id != current.employee_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not your payslip")
    if slip.payroll_run.status != "finalized":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Payroll run is not finalized yet")

    settings = org_service.get_settings(db)
    employee = db.get(Employee, slip.employee_id)
    pdf_bytes = render_payslip_pdf(slip.payroll_run, slip, employee, settings.company_name)
    headers = {"Content-Disposition": f'attachment; filename="payslip-{employee.code}-{slip.payroll_run.month}-{slip.payroll_run.year}.pdf"'}
    return Response(content=pdf_bytes, media_type="application/pdf", headers=headers)
