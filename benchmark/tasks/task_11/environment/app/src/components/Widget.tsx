import React from 'react';
import _ from 'lodash';
import moment from 'moment';

// Unoptimized widget component
export const Widget: React.FC<{ title: string; data: any[] }> = ({ title, data }) => {
  // Expensive computation on every render
  const processed = _.chain(data)
    .map(item => ({ ...item, processed: true }))
    .filter(item => item.value > 0)
    .sortBy('value')
    .reverse()
    .value();

  return (
    <div className="widget">
      <h3>{title}</h3>
      <p>Last updated: {moment().format('HH:mm:ss')}</p>
      <ul>
        {processed.map((item, idx) => (
          <li key={idx}>{item.value}</li>
        ))}
      </ul>
    </div>
  );
};
