# Dashboard App - Performance Optimization Task

This React 18 dashboard application has significant performance issues that need to be addressed.

## Current Issues

1. **No Webpack Optimization**: The webpack config has no optimization settings, code splitting, or tree shaking
2. **Large Bundle Size**: All dependencies (lodash, moment, chart.js) are bundled entirely
3. **No Code Splitting**: All code is in a single bundle.js file
4. **Unoptimized Components**: Components re-render unnecessarily and perform expensive computations on every render
5. **No Memoization**: No useMemo, useCallback, or React.memo usage
6. **Inefficient Imports**: Full library imports instead of tree-shakeable imports
7. **Large Data Sets**: Rendering 10,000+ items without virtualization

## Task Goal

Optimize the application to achieve a Lighthouse performance score of 90 or above.

## Expected Optimizations

- Configure webpack for production builds with code splitting
- Implement React performance optimizations (memo, useMemo, useCallback)
- Replace heavy dependencies with lighter alternatives (e.g., date-fns instead of moment, lodash-es with tree shaking)
- Implement virtual scrolling for large lists
- Optimize bundle size through tree shaking and chunk splitting
- Lazy load components and routes

## Running the Application

```bash
npm install
npm run build
npm start
```

## Running Lighthouse

```bash
lighthouse http://localhost:3000 --only-categories=performance
```
