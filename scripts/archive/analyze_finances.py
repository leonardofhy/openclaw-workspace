import pandas as pd
import json
from datetime import datetime

def analyze_finances(file_path):
    try:
        # Read Excel
        df = pd.read_excel(file_path)
        
        # Convert Period to datetime
        df['Period'] = pd.to_datetime(df['Period'])
        
        # Filter expenses only
        expenses = df[df['Income/Expense'] == 'Exp.'].copy()
        
        # Extract month
        expenses['Month'] = expenses['Period'].dt.to_period('M')
        
        # Get current and last month
        latest_month = expenses['Period'].max().to_period('M')
        last_month = (expenses['Period'].max() - pd.DateOffset(months=1)).to_period('M')
        
        # Calculate burn rates
        current_burn = expenses[expenses['Month'] == latest_month]['Amount'].sum()
        last_burn = expenses[expenses['Month'] == last_month]['Amount'].sum()
        
        # Total expenses
        total_exp = expenses['Amount'].sum()
        
        # Category breakdown (current month)
        category_breakdown = expenses[expenses['Month'] == latest_month].groupby('Category')['Amount'].sum().to_dict()
        
        stats = {
            "current_month": str(latest_month),
            "current_month_burn": float(current_burn),
            "last_month": str(last_month),
            "last_month_burn": float(last_burn),
            "total_expenses": float(total_exp),
            "category_breakdown": {k: float(v) for k, v in category_breakdown.items()},
            "last_updated": datetime.now().isoformat()
        }
        
        # Save to JSON
        with open("memory/finance_stats.json", "w") as f:
            json.dump(stats, f, indent=2, ensure_ascii=False)
        
        print(f"💰 {stats['last_month']} Burn: TWD {stats['last_month_burn']:.0f}")
        print(f"🔥 {stats['current_month']} Burn: TWD {stats['current_month_burn']:.0f}")
        print(f"\n📊 Category Breakdown ({stats['current_month']}):")
        for cat, amt in sorted(category_breakdown.items(), key=lambda x: -x[1]):
            print(f"  {cat}: TWD {amt:.0f}")
        
        return stats
            
    except Exception as e:
        print(f"❌ Analysis Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    analyze_finances("memory/finance_data/2026-02-19.xlsx")
