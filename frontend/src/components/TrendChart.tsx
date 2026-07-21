"use client";

import { useEffect, useRef } from "react";
import * as echarts from "echarts";

interface TrendChartProps {
  data: number[];
  labels: string[];
  title?: string;
}

export function TrendChart({ data, labels, title }: TrendChartProps) {
  const chartRef = useRef<HTMLDivElement>(null);
  const chartInstance = useRef<echarts.ECharts | null>(null);

  useEffect(() => {
    if (!chartRef.current) return;

    chartInstance.current = echarts.init(chartRef.current);

    const option: echarts.EChartsOption = {
      backgroundColor: "transparent",
      title: {
        text: title,
        textStyle: {
          color: "#ffffff",
          fontSize: 14,
        },
        left: "center",
      },
      tooltip: {
        trigger: "axis",
        backgroundColor: "#1a1a1a",
        borderColor: "#2a2a2a",
        textStyle: { color: "#ffffff" },
      },
      grid: {
        left: "10%",
        right: "10%",
        top: title ? "20%" : "5%",
        bottom: "10%",
      },
      xAxis: {
        type: "category",
        data: labels,
        axisLine: { lineStyle: { color: "#2a2a2a" } },
        axisLabel: { color: "#a1a1a1" },
      },
      yAxis: {
        type: "value",
        axisLine: { lineStyle: { color: "#2a2a2a" } },
        axisLabel: { color: "#a1a1a1" },
        splitLine: { lineStyle: { color: "#1a1a1a" } },
      },
      series: [
        {
          type: "line",
          data: data,
          smooth: true,
          lineStyle: {
            color: "#6366f1",
            width: 2,
          },
          areaStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: "rgba(99, 102, 241, 0.3)" },
              { offset: 1, color: "rgba(99, 102, 241, 0)" },
            ]),
          },
          itemStyle: {
            color: "#6366f1",
          },
        },
      ],
    };

    chartInstance.current.setOption(option);

    const handleResize = () => {
      chartInstance.current?.resize();
    };

    window.addEventListener("resize", handleResize);

    return () => {
      window.removeEventListener("resize", handleResize);
      chartInstance.current?.dispose();
    };
  }, [data, labels, title]);

  return <div ref={chartRef} className="echarts-container" />;
}
