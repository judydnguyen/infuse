import { createStore, combineReducers } from 'redux';
import _ from 'lodash';
import moment from 'moment';

// Intentionally bloated reducers with unnecessary computations
const dataReducer = (state = { items: [] }, action: any) => {
  switch (action.type) {
    case 'SET_DATA':
      // Unnecessary deep clone on every action
      const cloned = _.cloneDeep(state);
      // Unnecessary moment operations
      const timestamp = moment().format('YYYY-MM-DD HH:mm:ss');
      return {
        ...cloned,
        items: action.payload,
        lastUpdated: timestamp,
      };
    default:
      return state;
  }
};

const uiReducer = (state = { theme: 'light' }, action: any) => {
  switch (action.type) {
    case 'TOGGLE_THEME':
      return { ...state, theme: state.theme === 'light' ? 'dark' : 'light' };
    default:
      return state;
  }
};

const rootReducer = combineReducers({
  data: dataReducer,
  ui: uiReducer,
});

export const store = createStore(rootReducer);
