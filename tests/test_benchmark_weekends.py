from pathlib import Path
from datetime import date
import ast,sys,unittest,tempfile,io,csv
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from benchmark_weekends import clear_weekend_benchmark_values,is_weekend_date

class BenchmarkWeekendTests(unittest.TestCase):
 def test_only_eight_weekend_cells_change_and_all_88_columns_hold(self):
  dates=['2020-01-03','2020-01-04','2020-01-05','2020-01-11','2020-01-12','2020-01-13']
  old={'Date':dates,**{f'legacy_{i}':[str(i)+'.123456789']*6 for i in range(87)}}
  frame=pd.DataFrame({**old,'SOXX':['20']*6,'SMH':['10']*6});before=frame.copy(deep=True);out=clear_weekend_benchmark_values(frame)
  pd.testing.assert_frame_equal(frame,before);pd.testing.assert_frame_equal(out[list(old)],before[list(old)])
  self.assertEqual(list(out.columns),list(before.columns));self.assertEqual(out.index.tolist(),before.index.tolist());changes=[]
  for i in range(len(frame)):
   for col in frame.columns:
    if pd.isna(out.at[i,col])and not pd.isna(before.at[i,col]):changes.append((i,col))
  self.assertEqual(len(changes),8);self.assertTrue(all(col in ('SMH','SOXX')and is_weekend_date(dates[i])for i,col in changes))
  self.assertEqual(out.loc[~out['Date'].map(is_weekend_date),'SMH'].tolist(),['10','10'])
 def test_idempotent_and_missing_target_columns_are_noop(self):
  frame=pd.DataFrame({'Date':['2020-01-03','2020-01-04'],'SMH':[1.,2.],'SOXX':[3.,4.],'legacy':[5.,6.]});once=clear_weekend_benchmark_values(frame);pd.testing.assert_frame_equal(once,clear_weekend_benchmark_values(once))
  old=pd.DataFrame({'Date':['2020-01-04'],'NVDA':['1.234567890']});pd.testing.assert_frame_equal(old,clear_weekend_benchmark_values(old))
 def test_final_cleanup_undoes_ffill_and_cache_weekend_values(self):
  source=pd.DataFrame({'Date':['2020-01-03','2020-01-04','2020-01-06'],'SMH':[10.,float('nan'),12.],'SOXX':[20.,float('nan'),22.],'legacy':[1.,2.,3.]})
  filled=source.ffill();self.assertEqual(filled.loc[1,'SMH'],10.)
  cached=filled.copy();cached.loc[0,'SOXX']=19.87654321
  out=clear_weekend_benchmark_values(cached);self.assertTrue(pd.isna(out.loc[1,'SMH']));self.assertTrue(pd.isna(out.loc[1,'SOXX']));self.assertEqual(out.loc[0,'SOXX'],19.87654321);pd.testing.assert_series_equal(out['legacy'],cached['legacy'])
 def test_invalid_or_missing_date_fails_before_serialization(self):
  with self.assertRaises(ValueError):clear_weekend_benchmark_values(pd.DataFrame({'SMH':[1.]}))
  with self.assertRaises(ValueError):clear_weekend_benchmark_values(pd.DataFrame({'Date':['2020-99-99'],'SMH':[1.]}))
 def test_recovery_fetch_maps_and_final_call_keep_two_columns(self):
  path=ROOT/'scripts/fetch_data.py'
  if not path.exists():self.skipTest('runner has no fetch source')
  tree=ast.parse(path.read_text());main=next(n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name=='main');mapping=next(n for n in main.body if isinstance(n,ast.Assign)and any(isinstance(a,ast.Name)and a.id=='symbol_map'for a in n.targets));symbols=ast.literal_eval(mapping.value)
  self.assertEqual(symbols['SMH'],['SMH']);self.assertEqual(symbols['SOXX'],['SOXX']);order=list(symbols);self.assertLess(order.index('KLAC'),order.index('SMH'));self.assertLess(order.index('SOXX'),order.index('PLTR'));self.assertLess(order.index('CRDO'),order.index('ALAB'))
  calls=[n for n in ast.walk(main)if isinstance(n,ast.Call)and isinstance(n.func,ast.Name)and n.func.id=='clear_weekend_benchmark_values'];self.assertEqual(len(calls),1)
  serialized=[n.lineno for n in ast.walk(main)if isinstance(n,ast.Call)and isinstance(n.func,ast.Attribute)and n.func.attr=='to_csv'];self.assertTrue(serialized);self.assertLess(calls[0].lineno,min(serialized))

if __name__=='__main__':unittest.main()
