import plotly.express as px
import plotly.graph_objects as go

def plot_piecharts(labels_counts,value_counts,total_count):

    fig = go.Figure(data=[go.Pie(
                        labels=labels_counts,
                        values=value_counts.values,
                        hole=0.3,
                        textinfo='percent',  # Show percentage
                        insidetextorientation='radial'
                    )])

    fig.update_layout( 
                            height=400,  # Height of the pie chart
                            width=300,  # Width of the pie chart
                            showlegend=True,  # Ensure the legend is visible
                            legend_title=dict(
                                text=f"<b style='font-size:18px; color:#FF8C00;'>Total Count: {total_count}</b>",  # Increase size & bold text
                                font=dict(size=20, color="#FF8C00"),  # Dark grey color for better visibility
                            ),
                            legend=dict(
                                orientation="v",  # Vertical legend layout
                                yanchor="top",
                                y=-0.1,  # Move the legend below the pie chart
                                xanchor="center",
                                x=0.5,  # Center-align legend
                                font=dict(size=16, color="#4B5563"),  # Increase font size for labels
                                bgcolor="rgba(255,255,255,1)",  # Pure white colo
                                bordercolor="#E5E7EB",  # Subtle gray border
                                borderwidth=1.5,  # Slight border for distinction
                        ),
                            margin=dict(t=50, b=150, l=50, r=50),  # Add extra margin at the bottom for the legend
                            plot_bgcolor="rgba(0,0,0,0)",  # Transparent background for the chart area
                            paper_bgcolor="rgba(255,255,255,1)",  # White background for the figure
                        )

    fig.update_layout(
                        legend=dict(
                        traceorder="normal",  # Keep labels in the same order as data
                        valign="middle",  # Vertically align items to the middle of the space
                        itemwidth=75,  # Increase the horizontal space for each label 
                        )
                    )

                # Remove scrolling by dynamically adjusting height for the legend
    max_legend_rows = len(value_counts) // 3 + 1  # Dynamically calculate rows based on labels
    fig.update_layout(height=400 + max_legend_rows * 40,)  # Increase height to fit all labels

    return fig

   