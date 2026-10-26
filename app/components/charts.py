"""Plotly chart helpers with consistent Truck/Rail colors."""

from __future__ import annotations

import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

from src.config import MODE_COLORS


CHART_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(232,238,243,0.55)",
    font=dict(family="IBM Plex Sans, Source Sans 3, sans-serif", size=13, color="#0F1C2E"),
    margin=dict(l=10, r=10, t=40, b=10),
)


def style_fig(fig: go.Figure, title: str) -> go.Figure:
    fig.update_layout(title=dict(text=title, x=0, xanchor="left"), **CHART_LAYOUT)
    fig.update_xaxes(gridcolor="#E5E1D8", zeroline=False)
    fig.update_yaxes(gridcolor="#E5E1D8", zeroline=False)
    return fig


def corridor_bar(df: pd.DataFrame, metric: str, metric_label: str) -> go.Figure:
    if df.empty:
        fig = go.Figure()
        fig.add_annotation(text="No flows for this selection", showarrow=False)
        return style_fig(fig, f"Top corridors by {metric_label}")
    plot_df = df.sort_values(metric, ascending=True)
    fig = px.bar(
        plot_df,
        x=metric,
        y="corridor",
        orientation="h",
        text=plot_df[metric].map(lambda v: f"{v:,.0f}"),
        color_discrete_sequence=["#1B4F72"],
    )
    fig.update_traces(textposition="outside", cliponaxis=False)
    fig.update_layout(yaxis_title="", xaxis_title=metric_label, height=420)
    return style_fig(fig, f"Top corridors by {metric_label}")


def mode_donut(df: pd.DataFrame, metric: str, metric_label: str) -> go.Figure:
    if df.empty:
        fig = go.Figure()
        fig.add_annotation(text="No flows for this selection", showarrow=False)
        return style_fig(fig, f"Mode mix — {metric_label}")
    colors = [MODE_COLORS.get(m, "#95A5A6") for m in df["mode_label"]]
    fig = go.Figure(
        data=[
            go.Pie(
                labels=df["mode_label"],
                values=df[metric],
                hole=0.45,
                marker=dict(colors=colors),
                textinfo="label+percent",
                hovertemplate="%{label}<br>%{value:,.1f}<br>%{percent}<extra></extra>",
            )
        ]
    )
    fig.update_layout(height=380, showlegend=False)
    return style_fig(fig, f"Mode mix — {metric_label}")


def commodity_bar(df: pd.DataFrame, metric: str, metric_label: str) -> go.Figure:
    if df.empty:
        fig = go.Figure()
        fig.add_annotation(text="No flows for this selection", showarrow=False)
        return style_fig(fig, f"Top commodities by {metric_label}")
    plot_df = df.sort_values(metric, ascending=True)
    fig = px.bar(
        plot_df,
        x=metric,
        y="commodity_label",
        orientation="h",
        color_discrete_sequence=["#C45C26"],
        text=plot_df[metric].map(lambda v: f"{v:,.0f}"),
    )
    fig.update_traces(textposition="outside", cliponaxis=False)
    fig.update_layout(yaxis_title="", xaxis_title=metric_label, height=420)
    return style_fig(fig, f"Top commodities by {metric_label}")


def scenario_before_after(delta: pd.DataFrame) -> go.Figure:
    if delta.empty:
        fig = go.Figure()
        fig.add_annotation(text="No scenario data", showarrow=False)
        return style_fig(fig, "Mode share before vs after")
    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            name="Before",
            x=delta["mode_label"],
            y=delta["share_before"] * 100,
            marker_color="#8B7355",
        )
    )
    fig.add_trace(
        go.Bar(
            name="After",
            x=delta["mode_label"],
            y=delta["share_after"] * 100,
            marker_color="#1B4F72",
        )
    )
    fig.update_layout(
        barmode="group",
        yaxis_title="Share of tons (%)",
        xaxis_title="",
        height=380,
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )
    return style_fig(fig, "Mode share before vs after truck→rail shift")
