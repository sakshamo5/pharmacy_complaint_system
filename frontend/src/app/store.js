import { configureStore } from '@reduxjs/toolkit';
import complaintReducer from '../features/complaint/complaintSlice';
import agentReducer from '../features/agent/agentSlice';
import riskReducer from '../features/riskAssessment/riskSlice';

export const store = configureStore({
  reducer: {
    complaint: complaintReducer,
    agent: agentReducer,
    risk: riskReducer,
  },
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware({
      // Allow non-serializable values in agent messages (File objects etc.)
      serializableCheck: {
        ignoredActions: ['agent/setUploadFile'],
        ignoredPaths: ['agent.uploadFile'],
      },
    }),
});

export default store;
