import React, { useState, useEffect } from 'react';
import { useSelector, useDispatch } from 'react-redux';
import _ from 'lodash';
import moment from 'moment';
import { Chart as ChartJS, CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend } from 'chart.js';
import { Line } from 'react-chartjs-2';
import './Dashboard.css';

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend);

// Intentionally unoptimized component with performance issues
export const Dashboard: React.FC = () => {
  const dispatch = useDispatch();
  const data = useSelector((state: any) => state.data);
  const [localData, setLocalData] = useState<any[]>([]);
  const [filteredData, setFilteredData] = useState<any[]>([]);

  // Problem 1: Creating massive arrays on every render
  useEffect(() => {
    // Generating 10,000 items unnecessarily
    const items = _.range(0, 10000).map(i => ({
      id: i,
      value: Math.random() * 1000,
      timestamp: moment().subtract(i, 'minutes').toISOString(),
      category: `Category ${i % 10}`,
    }));
    setLocalData(items);
    dispatch({ type: 'SET_DATA', payload: items });
  }, [dispatch]);

  // Problem 2: Expensive filtering on every render without memoization
  useEffect(() => {
    // Using expensive lodash operations
    const filtered = _.chain(localData)
      .filter(item => item.value > 100)
      .groupBy('category')
      .mapValues(group => _.sumBy(group, 'value'))
      .toPairs()
      .map(([key, value]) => ({ category: key, total: value }))
      .value();
    setFilteredData(filtered);
  }, [localData]);

  // Problem 3: Recomputing chart data on every render
  const chartData = {
    labels: localData.slice(0, 100).map(item => moment(item.timestamp).format('HH:mm')),
    datasets: [
      {
        label: 'Values',
        data: localData.slice(0, 100).map(item => item.value),
        borderColor: 'rgb(75, 192, 192)',
        backgroundColor: 'rgba(75, 192, 192, 0.2)',
      },
    ],
  };

  // Problem 4: Rendering all items without virtualization
  return (
    <div className="dashboard">
      <header className="dashboard-header">
        <h1>Dashboard</h1>
        <p>Last updated: {moment().format('YYYY-MM-DD HH:mm:ss')}</p>
      </header>
      
      <div className="dashboard-content">
        <div className="chart-section">
          <h2>Data Chart</h2>
          <div className="chart-container">
            <Line data={chartData} options={{ responsive: true }} />
          </div>
        </div>

        <div className="stats-section">
          <h2>Statistics</h2>
          <div className="stats-grid">
            <div className="stat-card">
              <h3>Total Items</h3>
              <p>{localData.length}</p>
            </div>
            <div className="stat-card">
              <h3>Filtered Items</h3>
              <p>{filteredData.length}</p>
            </div>
            <div className="stat-card">
              <h3>Average Value</h3>
              <p>{_.meanBy(localData, 'value').toFixed(2)}</p>
            </div>
          </div>
        </div>

        <div className="data-section">
          <h2>All Data Items</h2>
          {/* Problem 5: Rendering 10,000 items without virtualization */}
          <div className="data-list">
            {localData.map(item => (
              <div key={item.id} className="data-item">
                <span>ID: {item.id}</span>
                <span>Value: {item.value.toFixed(2)}</span>
                <span>Time: {moment(item.timestamp).format('HH:mm:ss')}</span>
                <span>Category: {item.category}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};
