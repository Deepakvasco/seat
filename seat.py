import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from io import BytesIO
import altair as alt
from datetime import datetime

# Page configuration
st.set_page_config(
    page_title="Seat Allocation Optimizer",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for professional styling
st.markdown("""
<style>
    /* Main title */
    .main-title {
        font-size: 2.8rem;
        color: #1E3A8A;
        text-align: center;
        margin-bottom: 0.5rem;
        font-weight: 800;
        padding-bottom: 0.5rem;
    }
    
    .subtitle {
        text-align: center;
        color: #6B7280;
        margin-bottom: 2rem;
        font-size: 1.1rem;
    }
    
    /* Section headers */
    .section-header {
        font-size: 1.5rem;
        color: #1E40AF;
        margin-top: 1.5rem;
        margin-bottom: 1rem;
        padding-left: 0.5rem;
        border-left: 4px solid #3B82F6;
        font-weight: 600;
    }
    
    /* Total seats banner */
    .total-banner {
        background: linear-gradient(135deg, #1E3A8A 0%, #3B82F6 100%);
        color: white;
        padding: 0.5rem 1rem;
        border-radius: 8px;
        text-align: center;
        font-weight: bold;
        font-size: 1.2rem;
        margin-bottom: 1rem;
    }
    
    /* Data table styling */
    .data-table-container {
        border: 1px solid #E5E7EB;
        border-radius: 10px;
        overflow: hidden;
        margin-bottom: 1rem;
    }
    
    /* Highlight for Party 1 */
    .party-1-row {
        background-color: #F0F9FF !important;
        font-weight: 600 !important;
    }
    
    /* Footer */
    .footer {
        text-align: center;
        color: #6B7280;
        font-size: 0.85rem;
        margin-top: 2rem;
        padding-top: 1rem;
        border-top: 1px solid #E5E7EB;
    }
    
    /* Warning box */
    .warning-box {
        background-color: #FEF3C7;
        border-left: 4px solid #F59E0B;
        padding: 1rem;
        border-radius: 6px;
        margin: 1rem 0;
    }
    
    /* Success box */
    .success-box {
        background-color: #D1FAE5;
        border-left: 4px solid #10B981;
        padding: 1rem;
        border-radius: 6px;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# Title
st.markdown('<h1 class="main-title">🏛️ Seat Allocation Optimizer</h1>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Strategic seat distribution across 234 constituencies • Zero-sum allocation model</div>', unsafe_allow_html=True)

# Initialize session state
if 'original_data' not in st.session_state:
    # Initial data
    initial_data = {
        'Party': [f'Party {i}' for i in range(1, 23)],
        'Good': [168, 2, 1, 1, 1, 0, 1, 4, 22, 6, 4, 4, 2, 1, 1, 1, 1, 1, 1, 5, 6, 1],
        'Neutral': [163, 2, 1, 1, 1, 0, 1, 4, 24, 7, 5, 5, 2, 1, 1, 1, 1, 1, 1, 5, 6, 1],
        'Worst': [158, 2, 2, 1, 1, 0, 1, 4, 25, 8, 5, 5, 2, 1, 1, 1, 1, 1, 1, 6, 7, 1]
    }
    st.session_state.original_data = pd.DataFrame(initial_data)
    st.session_state.current_data = st.session_state.original_data.copy()
    st.session_state.scenario = 'Good'

# Constants
TOTAL_SEATS = 234

# Functions
def balance_seats(df, changed_col, changed_idx, new_value):
    """
    Zero-sum seat balancing:
    - If Party 1 gains seats, allies lose proportionally
    - If Party 1 loses seats, allies gain proportionally
    - If ally gains seats, Party 1 loses seats
    - If ally loses seats, Party 1 gains seats
    """
    df_balanced = df.copy()
    
    for scenario in ['Good', 'Neutral', 'Worst']:
        current_total = df_balanced[scenario].sum()
        
        # If total is not 234, adjust Party 1 to make it 234
        if current_total != TOTAL_SEATS:
            difference = TOTAL_SEATS - current_total
            df_balanced.at[0, scenario] += difference
            df_balanced.at[0, scenario] = max(0, min(TOTAL_SEATS, df_balanced.at[0, scenario]))
    
    return df_balanced

def adjust_all_scenarios(df, changed_scenario, changed_idx, new_value):
    """Adjust all scenarios when one is changed"""
    df_adjusted = df.copy()
    
    # For each scenario
    for scenario in ['Good', 'Neutral', 'Worst']:
        if scenario == changed_scenario:
            continue
            
        # Get the ratio from the changed scenario
        if changed_idx == 0:  # Party 1 changed
            # Maintain similar ratios for other scenarios
            old_party1_val = df.at[0, changed_scenario]
            if old_party1_val > 0:
                ratio = new_value / old_party1_val
                df_adjusted.at[0, scenario] = int(df.at[0, scenario] * ratio)
                df_adjusted.at[0, scenario] = max(0, min(TOTAL_SEATS, df_adjusted.at[0, scenario]))
        else:  # Ally changed
            old_ally_val = df.at[changed_idx, changed_scenario]
            if old_ally_val > 0:
                ratio = new_value / old_ally_val
                df_adjusted.at[changed_idx, scenario] = int(df.at[changed_idx, scenario] * ratio)
                df_adjusted.at[changed_idx, scenario] = max(0, df_adjusted.at[changed_idx, scenario])
    
    return df_adjusted

def get_scenario_summary(df, scenario):
    """Get summary for a scenario"""
    party1_seats = df.at[0, scenario]
    ally_seats = df.iloc[1:][scenario].sum()
    zero_seat_allies = (df.iloc[1:][scenario] == 0).sum()
    
    return {
        'Party 1 Seats': party1_seats,
        'Party 1 %': f"{(party1_seats/TOTAL_SEATS*100):.1f}%",
        'Ally Seats': ally_seats,
        'Zero Seat Allies': zero_seat_allies,
        'Allocation': f"{df[scenario].sum()}/{TOTAL_SEATS}"
    }

# Sidebar
with st.sidebar:
    st.markdown("### ⚙️ Dashboard Settings")
    
    # Scenario selector
    scenario = st.selectbox(
        "**Primary Scenario**",
        ["Good", "Neutral", "Worst"],
        index=0,
        help="Select the primary scenario to analyze"
    )
    
    # Port selection (for running on different ports)
    port_info = st.expander("🖥️ Deployment Settings")
    with port_info:
        st.info("""
        **To run on different ports:**
        ```
        streamlit run app.py --server.port 8501
        streamlit run app.py --server.port 8502
        streamlit run app.py --server.port 8503
        ```
        """)
    
    st.markdown("---")
    st.markdown("### 📊 Current Totals")
    
    # Display current totals
    for sc in ['Good', 'Neutral', 'Worst']:
        total = st.session_state.current_data[sc].sum()
        status = "✅" if total == TOTAL_SEATS else "⚠️"
        st.metric(f"{sc} Scenario", total, delta=status)
    
    st.markdown("---")
    st.markdown("### 📁 Data Management")
    
    # Reset button
    if st.button("🔄 Reset to Default", use_container_width=True, type="secondary"):
        st.session_state.current_data = st.session_state.original_data.copy()
        st.rerun()
    
    # File upload
    uploaded_file = st.file_uploader(
        "Upload Custom Data",
        type=['xlsx', 'csv'],
        help="Upload Excel/CSV with Party, Good, Neutral, Worst columns"
    )
    
    if uploaded_file:
        try:
            if uploaded_file.name.endswith('.csv'):
                new_df = pd.read_csv(uploaded_file)
            else:
                new_df = pd.read_excel(uploaded_file)
            
            if all(col in new_df.columns for col in ['Party', 'Good', 'Neutral', 'Worst']):
                # Ensure Party 1 is first
                if new_df['Party'].iloc[0] != 'Party 1':
                    # Find and move Party 1 to top
                    party1_idx = new_df[new_df['Party'] == 'Party 1'].index
                    if len(party1_idx) > 0:
                        party1_row = new_df.loc[party1_idx].copy()
                        new_df = new_df.drop(party1_idx)
                        new_df = pd.concat([party1_row, new_df]).reset_index(drop=True)
                
                st.session_state.current_data = new_df
                st.success("Data uploaded successfully!")
                st.rerun()
        except Exception as e:
            st.error(f"Error: {str(e)}")

# Main Content Area
st.markdown(f'<div class="total-banner">🎯 Total Seats Always: {TOTAL_SEATS} | Selected Scenario: {scenario}</div>', unsafe_allow_html=True)

# Row 1: Key Metrics
col1, col2, col3, col4 = st.columns(4)

with col1:
    party1_seats = st.session_state.current_data.at[0, scenario]
    st.metric("Party 1 Seats", party1_seats, 
              delta=f"{(party1_seats/TOTAL_SEATS*100):.1f}%")

with col2:
    ally_seats = st.session_state.current_data.iloc[1:][scenario].sum()
    st.metric("Allies Total", ally_seats)

with col3:
    active_allies = (st.session_state.current_data.iloc[1:][scenario] > 0).sum()
    total_allies = len(st.session_state.current_data) - 1
    st.metric("Active Allies", f"{active_allies}/{total_allies}")

with col4:
    allocation = st.session_state.current_data[scenario].sum()
    st.metric("Allocated", f"{allocation}/{TOTAL_SEATS}", 
              delta="FULL" if allocation == TOTAL_SEATS else f"SHORT: {TOTAL_SEATS-allocation}")

# Row 2: Seat Allocation Editor
st.markdown('<div class="section-header">📝 Seat Allocation Editor</div>', unsafe_allow_html=True)

st.markdown("""
<div class="warning-box">
    ⚖️ **Zero-Sum Allocation Rules:**
    
</div>
""", unsafe_allow_html=True)

# Create a copy for editing
df_for_edit = st.session_state.current_data.copy()

# Display only Party and selected scenario columns
display_cols = ['Party', scenario]
display_df = df_for_edit[display_cols].copy()

# Add a "Total" row
total_row = pd.DataFrame({
    'Party': ['**TOTAL**'],
    scenario: [display_df[scenario].sum()]
})
display_df = pd.concat([display_df, total_row], ignore_index=True)

# Create editable table
edited_df = st.data_editor(
    display_df.iloc[:-1],  # Exclude total row from editing
    column_config={
        "Party": st.column_config.TextColumn("Party", width="medium"),
        scenario: st.column_config.NumberColumn(
            scenario,
            min_value=0,
            max_value=TOTAL_SEATS,
            step=1,
            format="%d",
            help=f"Seats allocated in {scenario} scenario"
        )
    },
    hide_index=True,
    use_container_width=True,
    num_rows="fixed",
    key=f"editor_{scenario}"
)

# Update logic when data is edited
if not edited_df.equals(display_df.iloc[:-1]):
    # Find what changed
    for idx in range(len(edited_df)):
        old_val = display_df.at[idx, scenario]
        new_val = edited_df.at[idx, scenario]
        
        if old_val != new_val:
            # Apply zero-sum balancing
            updated_data = st.session_state.current_data.copy()
            
            if idx == 0:  # Party 1 changed
                # Party 1 changed: adjust all allies proportionally
                difference = new_val - old_val
                total_ally_seats = updated_data.iloc[1:][scenario].sum()
                
                if total_ally_seats > 0 and difference != 0:
                    # Adjust each ally proportionally
                    for i in range(1, len(updated_data)):
                        proportion = updated_data.at[i, scenario] / total_ally_seats
                        adjustment = int(difference * proportion)
                        updated_data.at[i, scenario] = max(0, updated_data.at[i, scenario] - adjustment)
                
                updated_data.at[0, scenario] = new_val
            else:  # Ally changed
                # Ally changed: adjust Party 1 inversely
                difference = new_val - old_val
                updated_data.at[idx, scenario] = new_val
                updated_data.at[0, scenario] = max(0, updated_data.at[0, scenario] - difference)
            
            # Adjust other scenarios proportionally
            if scenario == 'Good':
                # Adjust Neutral and Worst based on Good changes
                for other_scenario in ['Neutral', 'Worst']:
                    if idx == 0:  # Party 1 changed
                        ratio = new_val / old_val if old_val > 0 else 1
                        updated_data.at[0, other_scenario] = int(updated_data.at[0, other_scenario] * ratio)
                    else:  # Ally changed
                        ratio = new_val / old_val if old_val > 0 else 1
                        updated_data.at[idx, other_scenario] = int(updated_data.at[idx, other_scenario] * ratio)
            
            # Ensure totals are correct
            for sc in ['Good', 'Neutral', 'Worst']:
                current_total = updated_data[sc].sum()
                if current_total != TOTAL_SEATS:
                    # Adjust Party 1 to fix total
                    difference = TOTAL_SEATS - current_total
                    updated_data.at[0, sc] += difference
                    updated_data.at[0, sc] = max(0, min(TOTAL_SEATS, updated_data.at[0, sc]))
            
            st.session_state.current_data = updated_data
            st.rerun()

# Display totals
st.markdown("---")
col1, col2, col3 = st.columns(3)

with col1:
    good_total = st.session_state.current_data['Good'].sum()
    status = "✅" if good_total == TOTAL_SEATS else "⚠️"
    st.metric("Good Scenario", good_total, delta=status)

with col2:
    neutral_total = st.session_state.current_data['Neutral'].sum()
    status = "✅" if neutral_total == TOTAL_SEATS else "⚠️"
    st.metric("Neutral Scenario", neutral_total, delta=status)

with col3:
    worst_total = st.session_state.current_data['Worst'].sum()
    status = "✅" if worst_total == TOTAL_SEATS else "⚠️"
    st.metric("Worst Scenario", worst_total, delta=status)

# Row 3: Visualization
st.markdown('<div class="section-header">📊 Visualization</div>', unsafe_allow_html=True)

tab1, tab2, tab3 = st.tabs(["Bar Chart", "Pie Chart", "Comparison"])

with tab1:
    # Bar chart for selected scenario
    plot_data = st.session_state.current_data.copy()
    plot_data = plot_data.sort_values(by=scenario, ascending=False).head(10)
    
    fig = px.bar(
        plot_data,
        x='Party',
        y=scenario,
        title=f"Top 10 Parties - {scenario} Scenario",
        labels={scenario: 'Seats', 'Party': 'Party'},
        color=scenario,
        color_continuous_scale='blues'
    )
    
    # Add horizontal line at majority (117) and super majority (150)
    fig.add_hline(y=117, line_dash="dash", line_color="orange", 
                  annotation_text="Simple Majority (117)", 
                  annotation_position="bottom right")
    fig.add_hline(y=150, line_dash="dash", line_color="red", 
                  annotation_text="Strong Majority (150)", 
                  annotation_position="bottom right")
    
    fig.update_layout(showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

with tab2:
    col1, col2 = st.columns(2)
    
    with col1:
        # Pie chart for Good scenario
        good_data = st.session_state.current_data[st.session_state.current_data['Good'] > 0].head(8)
        if len(good_data) > 0:
            fig_good = px.pie(
                good_data,
                values='Good',
                names='Party',
                title='Good Scenario - Top 8 Parties',
                hole=0.4,
                color_discrete_sequence=px.colors.sequential.Blues
            )
            st.plotly_chart(fig_good, use_container_width=True)
    
    with col2:
        # Pie chart for Worst scenario
        worst_data = st.session_state.current_data[st.session_state.current_data['Worst'] > 0].head(8)
        if len(worst_data) > 0:
            fig_worst = px.pie(
                worst_data,
                values='Worst',
                names='Party',
                title='Worst Scenario - Top 8 Parties',
                hole=0.4,
                color_discrete_sequence=px.colors.sequential.Reds
            )
            st.plotly_chart(fig_worst, use_container_width=True)

with tab3:
    # Scenario comparison for top parties
    top_parties = st.session_state.current_data.nlargest(6, 'Good')['Party'].tolist()
    comparison_data = st.session_state.current_data[st.session_state.current_data['Party'].isin(top_parties)]
    
    # Melt data for Altair
    melted_data = comparison_data.melt(
        id_vars=['Party'],
        value_vars=['Good', 'Neutral', 'Worst'],
        var_name='Scenario',
        value_name='Seats'
    )
    
    chart = alt.Chart(melted_data).mark_bar().encode(
        x=alt.X('Party:N', title='Party', sort='-y'),
        y=alt.Y('Seats:Q', title='Seats'),
        color=alt.Color('Scenario:N', title='Scenario',
                       scale=alt.Scale(domain=['Good', 'Neutral', 'Worst'],
                                      range=['#10B981', '#3B82F6', '#EF4444'])),
        column=alt.Column('Scenario:N', title='')
    ).properties(
        width=200,
        height=400
    ).configure_view(
        stroke=None
    )
    
    st.altair_chart(chart, use_container_width=True)

# Row 4: Detailed Analysis
st.markdown('<div class="section-header">🔍 Detailed Analysis</div>', unsafe_allow_html=True)

col1, col2 = st.columns(2)

with col1:
    st.markdown("### Scenario Summary")
    
    summary_data = []
    for sc in ['Good', 'Neutral', 'Worst']:
        summary = get_scenario_summary(st.session_state.current_data, sc)
        summary_data.append({
            'Scenario': sc,
            'Party 1 Seats': summary['Party 1 Seats'],
            'Party 1 %': summary['Party 1 %'],
            'Allies Total': summary['Ally Seats'],
            'Zero Allies': summary['Zero Seat Allies']
        })
    
    summary_df = pd.DataFrame(summary_data)
    st.dataframe(summary_df, use_container_width=True, hide_index=True)

with col2:
    st.markdown("### What-If Analysis")
    
    current_party1 = st.session_state.current_data.at[0, scenario]
    new_party1 = st.slider(
        f"Adjust Party 1 seats in {scenario}",
        min_value=100,
        max_value=200,
        value=int(current_party1),
        step=1
    )
    
    if new_party1 != current_party1:
        difference = new_party1 - current_party1
        total_ally_seats = st.session_state.current_data.iloc[1:][scenario].sum()
        
        if difference > 0:
            st.error(f"⚠️ Allies would lose {difference} seats total")
            
            # Show impact per ally
            if total_ally_seats > 0:
                st.markdown("**Impact per ally (approx):**")
                for i in range(1, min(6, len(st.session_state.current_data))):
                    ally_name = st.session_state.current_data.at[i, 'Party']
                    current_seats = st.session_state.current_data.at[i, scenario]
                    if current_seats > 0:
                        proportion = current_seats / total_ally_seats
                        loss = int(difference * proportion)
                        st.markdown(f"- {ally_name}: {current_seats} → {max(0, current_seats - loss)}")
        else:
            st.success(f"✅ Allies would gain {abs(difference)} seats total")

# Row 5: Export Section
st.markdown('<div class="section-header">💾 Export Data</div>', unsafe_allow_html=True)

col1, col2, col3 = st.columns(3)

with col1:
    # Export to Excel
    def to_excel(df):
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Seat_Allocation')
            
            # Add summary sheet
            summary_rows = []
            for sc in ['Good', 'Neutral', 'Worst']:
                summary = get_scenario_summary(df, sc)
                summary_rows.append({
                    'Scenario': sc,
                    'Party 1 Seats': summary['Party 1 Seats'],
                    'Party 1 %': summary['Party 1 %'],
                    'Allies Total': summary['Ally Seats'],
                    'Zero Seat Allies': summary['Zero Seat Allies']
                })
            
            summary_df = pd.DataFrame(summary_rows)
            summary_df.to_excel(writer, index=False, sheet_name='Summary')
        
        return output.getvalue()
    
    excel_data = to_excel(st.session_state.current_data)
    st.download_button(
        label="📥 Download Excel",
        data=excel_data,
        file_name=f"seat_allocation_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True
    )

with col2:
    # Export to CSV
    csv_data = st.session_state.current_data.to_csv(index=False)
    st.download_button(
        label="📥 Download CSV",
        data=csv_data,
        file_name=f"seat_allocation_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv",
        use_container_width=True
    )

with col3:
    st.markdown("### 🔗 Share Dashboard")
    st.info("""
    **Deploy on Streamlit Cloud:**
    1. Push code to GitHub
    2. Connect at share.streamlit.io
    3. Share public URL
    
    **Run locally on different ports:**
    ```bash
    streamlit run app.py --server.port 8501
    streamlit run app.py --server.port 8502
    ```
    """)

# Footer
st.markdown("---")
st.markdown("""
<div class="footer">
    <p>🏛️ <strong>Seat Allocation Optimizer v2.0</strong> | Production-Ready Dashboard</p>
    <p>📊 Zero-Sum Allocation Model | Total Seats: {TOTAL_SEATS} | Last Updated: {date}</p>
    <p style="color: #9CA3AF; font-size: 0.75rem; margin-top: 0.5rem;">
        This dashboard implements a zero-sum allocation model where Party 1 seat changes 
        inversely affect allies. Total seats always remain {TOTAL_SEATS}.
    </p>
</div>
""".format(TOTAL_SEATS=TOTAL_SEATS, date=datetime.now().strftime("%B %d, %Y %H:%M")), 
unsafe_allow_html=True)