import warnings
warnings.filterwarnings("ignore")

from tests.fixtures.universal_datasets import make_sales_df, make_clinical_df
from app.services.universal.profiler import build_data_profile

def show_profile(label, df):
    p = build_data_profile(df)
    print(f"\n{'='*60}")
    print(f"{label}")
    print(f"{'='*60}")
    print(f"Rows={p['row_count']}  Cols={p['col_count']}  Degraded={p['degraded_mode']}")
    print(f"Target column: {p['target_column']}")
    print(f"\n{'Column':<22} {'Type':<13} {'null%':>6}  Stats")
    print(f"{'-'*80}")
    for cp in p['columns']:
        s = cp.get('stats', {})
        t = cp['type']
        if t == 'numeric':
            extra = f"mean={s['mean']:.2f}  median={s['median']:.2f}  std={s['std']:.2f}  outliers={s['outlier_count']}"
        elif t == 'categorical':
            top5 = ", ".join(f"{tv['value']}({tv['pct']}%)" for tv in s.get('top_values', [])[:3])
            extra = f"uniq={s['unique_count']}  top: {top5}"
        elif t == 'datetime':
            extra = f"span={s['span_days']}d  [{s['min'][:10]}..{s['max'][:10]}]  gran={s['granularity']}"
        elif t == 'boolean':
            extra = f"true={s['true_count']}  false={s['false_count']}  true%={s['true_pct']}"
        else:
            extra = f"uniq={s['unique_count']}"
        print(f"  {cp['column']:<20} {t:<13} {cp['null_pct']:>6.1f}%  {extra}")

    print(f"\nCorrelation matrix covers: {list(p['correlation_matrix'].keys())}")
    print(f"GroupBy aggregates over:   {list(p['groupby_aggregates'].keys())}")
    if p['groupby_aggregates']:
        first_cat = list(p['groupby_aggregates'].keys())[0]
        first_num = list(p['groupby_aggregates'][first_cat].keys())[0]
        rows = p['groupby_aggregates'][first_cat][first_num]
        print(f"  Example: {first_cat} x {first_num}:")
        for r in rows:
            print(f"    {r['group']:<20} mean={r['mean']:.2f}  count={r['count']}")

show_profile("SALES DATASET (200 rows x 11 cols)", make_sales_df())
show_profile("CLINICAL DATASET (300 rows x 12 cols)", make_clinical_df())
