import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import deploy_via_git

cmd = """sudo docker exec ca-trader python3 -c "
import app, json
r = app.overall_recommendation('NIFTY', '15m')
out = {
    'recommendation': r.get('recommendation'),
    'signal': r.get('signal'),
    'action': r.get('action'),
    'option_type': r.get('option_type'),
    'underlying_rec': r.get('underlying_recommendation'),
    'call_is_primary': (r.get('call_option') or {}).get('is_primary'),
    'put_is_primary': (r.get('put_option') or {}).get('is_primary'),
    'confidence': r.get('confidence')
}
print(json.dumps(out, indent=2))
" """

res = deploy_via_git.run_ssh(cmd)
print("TEST RECO RESULT:")
print(res.stdout)

