from pathlib import Path
from datetime import date
import csv,tempfile,unittest
from scripts.normalize_snapshot_calendar import BOND_COLUMNS,synchronize_market_files

class HistoricalBenchmarkNormalizerTests(unittest.TestCase):
 def test_all_history_only_benchmark_weekend_cells_clear_and_mirrors_match(self):
  with tempfile.TemporaryDirectory()as d:
   root=Path(d);path=root/'data/market.csv';path.parent.mkdir();header=['Date','NVDA','SMH','SOXX',*BOND_COLUMNS]
   days=['2001-07-14','2001-07-15','2002-01-05','2002-01-06','2026-10-23'];rows=[{'Date':x,'NVDA':'1.234567890','SMH':'12.3456789','SOXX':'98.7654321',**{k:'0.123456789'for k in BOND_COLUMNS}}for x in days]
   with path.open('w',newline='')as f:w=csv.DictWriter(f,header,lineterminator='\n');w.writeheader();w.writerows(rows)
   cleared,dates=synchronize_market_files(root,35);self.assertEqual(cleared,8);self.assertEqual(dates,[date.fromisoformat(x)for x in days[:-1]])
   with path.open(newline='')as f:after=list(csv.DictReader(f))
   self.assertEqual(len(after),len(rows));self.assertEqual([r['Date']for r in after],days)
   for i,(old,new)in enumerate(zip(rows,after)):
    for k in header:
     self.assertEqual(new[k],''if i<4 and k in ('SMH','SOXX')else old[k])
   first=path.read_bytes();self.assertEqual(first,(root/'webapp/public/market.csv').read_bytes());self.assertEqual(first,(root/'webapp/data/market.csv').read_bytes())
   self.assertEqual(synchronize_market_files(root,35),(0,[]));self.assertEqual(first,path.read_bytes())
 def test_weekday_benchmarks_and_old_legacy_only_snapshots_unchanged(self):
  with tempfile.TemporaryDirectory()as d:
   root=Path(d);path=root/'data/market.csv';path.parent.mkdir();header=['Date','NVDA',*BOND_COLUMNS]
   with path.open('w',newline='')as f:w=csv.DictWriter(f,header,lineterminator='\n');w.writeheader();w.writerows([{'Date':'2001-07-14','NVDA':'1.2345'},{'Date':'2026-10-23',**{k:'1.1'for k in BOND_COLUMNS}}])
   before=path.read_bytes();self.assertEqual(synchronize_market_files(root,35),(0,[]));self.assertEqual(before,path.read_bytes())

if __name__=='__main__':unittest.main()
