import { createSlice } from '@reduxjs/toolkit';

/**
 * complaintSlice — manages the LEFT PANEL form state.
 *
 * The form is READ-ONLY — users cannot type into it.
 * All values are populated via populateFromAI() dispatched
 * when the SSE stream emits a "complaint_update" event.
 *
 * Field names match exactly the backend ComplaintData schema.
 */

const EMPTY_FORM = {
  complaintSource: '',
  customerName: '',
  customerContact: '',
  reporterType: '',
  productName: '',
  productStrength: '',
  productType: '',
  batchNumber: '',
  lotNumber: '',
  manufacturingDate: '',
  expiryDate: '',
  quantityAffected: '',
  complaintType: '',
  complaintDate: '',
  description: '',
  initialSeverity: '',
  priority: '',
};

const initialState = {
  ...EMPTY_FORM,
  complaintId: null,        // DB UUID — set after first save
  complaintNumber: null,    // e.g., "CC-2024-0048"
  status: 'Pending Triage',
  isLoading: false,
  filledFields: [],         // tracks which fields were just filled (for animation)
  isSaved: false,
};

// Snake_case → camelCase mapping (backend → frontend)
const FIELD_MAP = {
  complaint_source: 'complaintSource',
  customer_name: 'customerName',
  customer_contact: 'customerContact',
  reporter_type: 'reporterType',
  product_name: 'productName',
  product_strength: 'productStrength',
  product_type: 'productType',
  batch_number: 'batchNumber',
  lot_number: 'lotNumber',
  manufacturing_date: 'manufacturingDate',
  expiry_date: 'expiryDate',
  quantity_affected: 'quantityAffected',
  complaint_type: 'complaintType',
  complaint_date: 'complaintDate',
  description: 'description',
  initial_severity: 'initialSeverity',
  priority: 'priority',
};

const complaintSlice = createSlice({
  name: 'complaint',
  initialState,

  reducers: {
    /**
     * populateFromAI — the most important action.
     * Called when SSE emits "complaint_update".
     * Converts snake_case keys from backend to camelCase for the form.
     * Tracks which fields changed for the fill animation.
     */
    populateFromAI(state, action) {
      const data = action.payload;
      const newlyFilled = [];

      Object.entries(data).forEach(([backendKey, value]) => {
        const frontendKey = FIELD_MAP[backendKey] || backendKey;
        if (value !== null && value !== undefined && value !== '') {
          // Track fields that are being filled for animation
          if (!state[frontendKey]) {
            newlyFilled.push(frontendKey);
          }
          state[frontendKey] = String(value);
        }
      });

      state.filledFields = newlyFilled;
      state.isLoading = false;
    },

    setComplaintId(state, action) {
      state.complaintId = action.payload.id;
      state.complaintNumber = action.payload.number;
    },

    setStatus(state, action) {
      state.status = action.payload;
    },

    setLoading(state, action) {
      state.isLoading = action.payload;
    },

    clearFilledAnimation(state) {
      state.filledFields = [];
    },

    resetForm(state) {
      return { ...initialState };
    },

    markSaved(state) {
      state.isSaved = true;
      state.status = 'Under Investigation';
    },
  },
});

export const {
  populateFromAI,
  setComplaintId,
  setStatus,
  setLoading,
  clearFilledAnimation,
  resetForm,
  markSaved,
} = complaintSlice.actions;

export default complaintSlice.reducer;
