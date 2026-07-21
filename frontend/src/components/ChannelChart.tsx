"use client";

import { useEffect, useRef } from "react";
import * as echarts from "echarts";

interface ChannelData {
  name: string;
  value: number;
}

interface ChannelChartProps {
  data: ChannelData[];
  title?: string;
}

export function ChannelChart({ data, title }: ChannelChartProps) {
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
        trigger: "item",
        backgroundColor: "#1a1a1a",
        borderColor: "#2a2a2a",
        textStyle: { color: "#ffffff" },
      },
      legend: {
        orient: "vertical",
        right: "5%",
        top: "center",
        textStyle: { color: "#a1a1a1" },
      },
      series: [
        {
          type: "pie",
          radius: ["40%", "70%"],
          center: ["40%", "50%"],
          avoidLabelOverlap: false,
          itemStyle: {
            borderRadius: 4,
            borderColor: "#0f0f0f",
            borderWidth: 2,
          },
          label: {
            show: false,
          },
          emphasis: {
            label: {
              show: true,
              fontSize: 14,
              fontWeight: "bold",
              color: "#ffffff",
            },
          },
          labelLine: {
            show: false,
          },
          data: data.map((item, index) => ({
            ...item,
            itemStyle: {
              color: [
                "#6366f1", // primary
                "#8b5cf6", // purple
                "#ec4899", // pink
                "#f59e0b", // amber
                "#10b981", // emerald
                "#3b82f6", // blue
                "#ef4444", // red
                "#14b8a6", // teal
              ][index % 8],
            },
          })),
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
  }, [data, title]);

  return <div ref={chartRef} className="echarts-container" />;
}
