from app import db_exec
p = db_exec("SELECT status, exit_price, stop_loss, target, realized_pnl, reasons FROM positions WHERE id='740ed277eb1661f43b9bbfdf'", fetch="one")
print("POSITION DETAILS:", dict(p))

