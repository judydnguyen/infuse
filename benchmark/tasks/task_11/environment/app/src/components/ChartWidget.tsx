import React from 'react';
import { Line } from 'react-chartjs-2';
import _ from 'lodash';

export const ChartWidget: React.FC = () => {
  // Generating data on every render
  const data = _.range(0, 1000).map(i => ({
    x: i,
    y: Math.random() * 100,
  }));

  const chartData = {
    labels: data.map(d => d.x.toString()),
    datasets: [{
      label: 'Data',
      data: data.map(d => d.y),
      borderColor: 'rgb(255, 99, 132)',
    }],
  };

  return <Line data={chartData} />;
};
