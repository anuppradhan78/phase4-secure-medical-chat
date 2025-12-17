"""
Simple cost dashboard for displaying metrics in HTML format.

This module provides:
- HTML dashboard for cost metrics visualization
- Simple charts and tables for cost analysis
- Real-time metrics display
"""

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse
from datetime import datetime, timezone
from typing import Optional

from ..models import UserRole


router = APIRouter()

# Global LLM Gateway instance (initialized in main app)
_llm_gateway = None


def init_dashboard_router(llm_gateway):
    """Initialize the dashboard router with LLM gateway."""
    global _llm_gateway
    _llm_gateway = llm_gateway


@router.get("/dashboard", response_class=HTMLResponse)
async def cost_dashboard(
    period_hours: int = 24,
    user_role: Optional[str] = None
):
    """
    Display cost dashboard with metrics visualization.
    
    Args:
        period_hours: Time period for metrics (default: 24 hours)
        user_role: Optional user role filter
        
    Returns:
        HTML response with dashboard
    """
    if not _llm_gateway:
        raise HTTPException(status_code=500, detail="LLM Gateway not initialized")
    
    try:
        # Get metrics data
        metrics_data = _llm_gateway.get_metrics(period_hours)
        analytics_data = _llm_gateway.get_detailed_analytics(7)  # 7 days for trends
        optimization_data = _llm_gateway.get_optimization_report()
        expensive_queries = _llm_gateway.get_expensive_queries(5)
        cache_stats = _llm_gateway.get_cache_stats()
        
        # Generate HTML dashboard
        html_content = generate_dashboard_html(
            metrics_data,
            analytics_data,
            optimization_data,
            expensive_queries,
            cache_stats,
            period_hours
        )
        
        return HTMLResponse(content=html_content)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating dashboard: {str(e)}")


def generate_dashboard_html(
    metrics_data,
    analytics_data,
    optimization_data,
    expensive_queries,
    cache_stats,
    period_hours
) -> str:
    """Generate HTML content for the cost dashboard."""
    
    # Extract key metrics
    total_cost = metrics_data.get("total_cost_usd", 0)
    queries_today = metrics_data.get("queries_today", 0)
    cache_hit_rate = metrics_data.get("cache_hit_rate", 0)
    avg_latency = metrics_data.get("avg_latency_ms", 0)
    cost_by_model = metrics_data.get("cost_by_model", {})
    cost_by_role = metrics_data.get("cost_by_role", {})
    
    # Generate model breakdown chart data
    model_chart_data = []
    for model, cost in cost_by_model.items():
        percentage = (cost / total_cost * 100) if total_cost > 0 else 0
        model_chart_data.append(f"['{model}', {cost:.2f}]")
    
    # Generate role breakdown chart data
    role_chart_data = []
    for role, cost in cost_by_role.items():
        percentage = (cost / total_cost * 100) if total_cost > 0 else 0
        role_chart_data.append(f"['{role}', {cost:.2f}]")
    
    # Generate expensive queries table
    expensive_queries_html = ""
    for query in expensive_queries:
        expensive_queries_html += f"""
        <tr>
            <td>{query.get('timestamp', 'N/A')[:19]}</td>
            <td>{query.get('model', 'N/A')}</td>
            <td>${query.get('cost_usd', 0):.3f}</td>
            <td>{query.get('user_role', 'N/A')}</td>
            <td>{query.get('total_tokens', 0)}</td>
            <td>{'Yes' if query.get('cache_hit', False) else 'No'}</td>
        </tr>
        """
    
    # Generate recommendations
    recommendations_html = ""
    for rec in optimization_data.get("recommendations", []):
        priority_class = f"priority-{rec.get('priority', 'medium')}"
        recommendations_html += f"""
        <div class="recommendation {priority_class}">
            <h4>{rec.get('title', 'Optimization Recommendation')}</h4>
            <p><strong>Category:</strong> {rec.get('category', 'N/A')}</p>
            <p><strong>Priority:</strong> {rec.get('priority', 'medium').title()}</p>
            <p><strong>Description:</strong> {rec.get('description', 'No description available')}</p>
            <p><strong>Potential Savings:</strong> ${rec.get('potential_savings', 0):.2f}</p>
            <p><strong>Implementation:</strong> {rec.get('implementation', 'No implementation details')}</p>
        </div>
        """
    
    html_template = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Secure Medical Chat - Cost Dashboard</title>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <style>
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                margin: 0;
                padding: 20px;
                background-color: #f5f5f5;
                color: #333;
            }}
            .header {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 20px;
                border-radius: 10px;
                margin-bottom: 20px;
                text-align: center;
            }}
            .metrics-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                gap: 20px;
                margin-bottom: 30px;
            }}
            .metric-card {{
                background: white;
                padding: 20px;
                border-radius: 10px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                text-align: center;
            }}
            .metric-value {{
                font-size: 2em;
                font-weight: bold;
                color: #667eea;
                margin-bottom: 5px;
            }}
            .metric-label {{
                color: #666;
                font-size: 0.9em;
            }}
            .charts-section {{
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 20px;
                margin-bottom: 30px;
            }}
            .chart-container {{
                background: white;
                padding: 20px;
                border-radius: 10px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }}
            .chart-title {{
                text-align: center;
                margin-bottom: 20px;
                color: #333;
                font-size: 1.2em;
                font-weight: bold;
            }}
            .table-container {{
                background: white;
                padding: 20px;
                border-radius: 10px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                margin-bottom: 20px;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
            }}
            th, td {{
                padding: 12px;
                text-align: left;
                border-bottom: 1px solid #ddd;
            }}
            th {{
                background-color: #f8f9fa;
                font-weight: bold;
                color: #333;
            }}
            .recommendations {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                gap: 20px;
                margin-bottom: 20px;
            }}
            .recommendation {{
                background: white;
                padding: 20px;
                border-radius: 10px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                border-left: 4px solid #667eea;
            }}
            .recommendation.priority-high {{
                border-left-color: #e74c3c;
            }}
            .recommendation.priority-medium {{
                border-left-color: #f39c12;
            }}
            .recommendation.priority-low {{
                border-left-color: #27ae60;
            }}
            .recommendation h4 {{
                margin-top: 0;
                color: #333;
            }}
            .cache-stats {{
                background: white;
                padding: 20px;
                border-radius: 10px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                margin-bottom: 20px;
            }}
            .cache-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 15px;
            }}
            .cache-metric {{
                text-align: center;
                padding: 15px;
                background: #f8f9fa;
                border-radius: 8px;
            }}
            .cache-metric .value {{
                font-size: 1.5em;
                font-weight: bold;
                color: #667eea;
            }}
            .cache-metric .label {{
                color: #666;
                font-size: 0.9em;
                margin-top: 5px;
            }}
            .refresh-info {{
                text-align: center;
                color: #666;
                font-size: 0.9em;
                margin-top: 20px;
            }}
            @media (max-width: 768px) {{
                .charts-section {{
                    grid-template-columns: 1fr;
                }}
                .metrics-grid {{
                    grid-template-columns: 1fr;
                }}
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🏥 Secure Medical Chat - Cost Dashboard</h1>
            <p>Real-time cost tracking and optimization insights</p>
            <p><strong>Period:</strong> Last {period_hours} hours | <strong>Updated:</strong> {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC</p>
        </div>

        <!-- Key Metrics -->
        <div class="metrics-grid">
            <div class="metric-card">
                <div class="metric-value">${total_cost:.2f}</div>
                <div class="metric-label">Total Cost</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{queries_today}</div>
                <div class="metric-label">Queries Today</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{cache_hit_rate:.1%}</div>
                <div class="metric-label">Cache Hit Rate</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{avg_latency:.0f}ms</div>
                <div class="metric-label">Avg Latency</div>
            </div>
        </div>

        <!-- Charts -->
        <div class="charts-section">
            <div class="chart-container">
                <div class="chart-title">Cost by Model</div>
                <canvas id="modelChart" width="400" height="300"></canvas>
            </div>
            <div class="chart-container">
                <div class="chart-title">Cost by User Role</div>
                <canvas id="roleChart" width="400" height="300"></canvas>
            </div>
        </div>

        <!-- Cache Statistics -->
        <div class="cache-stats">
            <h3>Cache Performance</h3>
            <div class="cache-grid">
                <div class="cache-metric">
                    <div class="value">{cache_stats.get('basic_stats', {}).get('total_entries', 0)}</div>
                    <div class="label">Cache Entries</div>
                </div>
                <div class="cache-metric">
                    <div class="value">{cache_stats.get('performance_stats', {}).get('cache_hits', 0)}</div>
                    <div class="label">Cache Hits</div>
                </div>
                <div class="cache-metric">
                    <div class="value">{cache_stats.get('performance_stats', {}).get('cache_misses', 0)}</div>
                    <div class="label">Cache Misses</div>
                </div>
                <div class="cache-metric">
                    <div class="value">${cache_stats.get('effectiveness', {}).get('cost_savings_estimate', 0):.2f}</div>
                    <div class="label">Est. Savings</div>
                </div>
            </div>
        </div>

        <!-- Expensive Queries -->
        <div class="table-container">
            <h3>Most Expensive Queries</h3>
            <table>
                <thead>
                    <tr>
                        <th>Timestamp</th>
                        <th>Model</th>
                        <th>Cost</th>
                        <th>User Role</th>
                        <th>Tokens</th>
                        <th>Cache Hit</th>
                    </tr>
                </thead>
                <tbody>
                    {expensive_queries_html}
                </tbody>
            </table>
        </div>

        <!-- Optimization Recommendations -->
        <div class="table-container">
            <h3>Cost Optimization Recommendations</h3>
            <p><strong>Total Potential Savings:</strong> ${optimization_data.get('total_potential_savings', 0):.2f}</p>
            <div class="recommendations">
                {recommendations_html}
            </div>
        </div>

        <div class="refresh-info">
            Dashboard auto-refreshes every 30 seconds. Last updated: {datetime.now(timezone.utc).strftime('%H:%M:%S')} UTC
        </div>

        <script>
            // Model Chart
            const modelCtx = document.getElementById('modelChart').getContext('2d');
            const modelChart = new Chart(modelCtx, {{
                type: 'doughnut',
                data: {{
                    labels: {list(cost_by_model.keys())},
                    datasets: [{{
                        data: {list(cost_by_model.values())},
                        backgroundColor: [
                            '#667eea',
                            '#764ba2',
                            '#f093fb',
                            '#f5576c',
                            '#4facfe'
                        ],
                        borderWidth: 2,
                        borderColor: '#fff'
                    }}]
                }},
                options: {{
                    responsive: true,
                    plugins: {{
                        legend: {{
                            position: 'bottom'
                        }},
                        tooltip: {{
                            callbacks: {{
                                label: function(context) {{
                                    return context.label + ': $' + context.parsed.toFixed(2);
                                }}
                            }}
                        }}
                    }}
                }}
            }});

            // Role Chart
            const roleCtx = document.getElementById('roleChart').getContext('2d');
            const roleChart = new Chart(roleCtx, {{
                type: 'bar',
                data: {{
                    labels: {list(cost_by_role.keys())},
                    datasets: [{{
                        label: 'Cost ($)',
                        data: {list(cost_by_role.values())},
                        backgroundColor: 'rgba(102, 126, 234, 0.8)',
                        borderColor: 'rgba(102, 126, 234, 1)',
                        borderWidth: 1
                    }}]
                }},
                options: {{
                    responsive: true,
                    scales: {{
                        y: {{
                            beginAtZero: true,
                            ticks: {{
                                callback: function(value) {{
                                    return '$' + value.toFixed(2);
                                }}
                            }}
                        }}
                    }},
                    plugins: {{
                        legend: {{
                            display: false
                        }},
                        tooltip: {{
                            callbacks: {{
                                label: function(context) {{
                                    return 'Cost: $' + context.parsed.y.toFixed(2);
                                }}
                            }}
                        }}
                    }}
                }}
            }});

            // Auto-refresh every 30 seconds
            setTimeout(function() {{
                location.reload();
            }}, 30000);
        </script>
    </body>
    </html>
    """
    
    return html_template