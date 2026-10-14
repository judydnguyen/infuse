import React from 'react';
import _ from 'lodash';
import moment from 'moment';

export const Component11: React.FC = () => {
  const data = _.range(0, 100).map(i => ({ id: i, value: Math.random() }));
  const processed = _.chain(data).filter(d => d.value > 0.5).value();
  
  return (
    <div>
      <h4>Component 11</h4>
      <p>{moment().format('YYYY-MM-DD HH:mm:ss')}</p>
      <p>Items: {processed.length}</p>
    </div>
  );
};
