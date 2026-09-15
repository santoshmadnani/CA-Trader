# -*- coding: utf-8 -*-
from pathlib import Path

path = Path("terminal.html")
code = path.read_text(encoding="utf-8")

old_script_start = """<script>
  // ==============================================================================
  // RELEASE 45 AUTHORITATIVE DASHBOARD & QUANTITATIVE ENGINE
  // ==============================================================================

  // Safe global UI helpers
  const $ = id => document.getElementById(id);"""

new_script_start = """<script>
(function() {
  // ==============================================================================
  // RELEASE 45 AUTHORITATIVE DASHBOARD & QUANTITATIVE ENGINE
  // ==============================================================================

  // Safe isolated UI helpers
  const $ = id => document.getElementById(id);"""

assert old_script_start in code, "old_script_start not found"
code = code.replace(old_script_start, new_script_start, 1)

old_script_end = """    wirePureGreeksSim();
    updateAutoRecoDashboardStrip();
  }

</script>"""

new_script_end = """    wirePureGreeksSim();
    updateAutoRecoDashboardStrip();
  }
})();
</script>"""

assert old_script_end in code, "old_script_end not found"
code = code.replace(old_script_end, new_script_end, 1)

path.write_text(code, encoding="utf-8")
print(f"Wrapped final script in IIFE: {len(code):,} bytes")

