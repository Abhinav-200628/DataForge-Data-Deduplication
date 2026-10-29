import React, { useState } from 'react';
import { Modal } from '../common/Modal';
import { ReviewItem } from '../../types';
import { api } from '../../services/api';
import { AlertOctagon, CheckCircle2, XCircle, ShieldAlert } from 'lucide-react';

interface ReviewActionModalProps {
  isOpen: boolean;
  onClose: () => void;
  item: ReviewItem | null;
  onSuccess: () => void;
}

export const ReviewActionModal: React.FC<ReviewActionModalProps> = ({
  isOpen,
  onClose,
  item,
  onSuccess,
}) => {
  const [selectedAction, setSelectedAction] = useState<'APPROVED' | 'REJECTED' | 'RESOLVED'>('APPROVED');
  const [notes, setNotes] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen || !item) return null;

  const hasHardConflicts = item.reasons.some(
    (r) => r.toLowerCase().includes('hard conflict') || r.toLowerCase().includes('conflicting')
  );

  const handleSubmit = async () => {
    if (selectedAction === 'APPROVED' && hasHardConflicts) {
      setError('Cannot approve an automatic merge with unresolved hard conflicts (Tax ID / DOB / UPC mismatch).');
      return;
    }

    setSubmitting(true);
    setError(null);
    try {
      await api.updateReviewAction(item.review_id, selectedAction, notes);
      onSuccess();
      onClose();
    } catch (err: any) {
      setError(err.message || 'Failed to update review status.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Triage Manual Review Candidate"
      subtitle={`Review ID: ${item.review_id} • System: ${item.source_system}`}
      maxWidth="lg"
    >
      <div className="space-y-5 text-xs">
        {/* Candidate Summary */}
        <div className="p-4 rounded-xl bg-[#0D1423] border border-[#1C283F] space-y-2">
          <div className="flex justify-between items-center text-slate-300">
            <span>Source Record:</span>
            <span className="font-mono font-bold text-white">{item.source_record_id}</span>
          </div>
          <div className="flex justify-between items-center text-slate-300">
            <span>Entity Domain:</span>
            <span className="font-mono text-cyan-400 font-semibold">{item.entity_type}</span>
          </div>
          {item.similarity_score !== null && (
            <div className="flex justify-between items-center text-slate-300">
              <span>Similarity Score:</span>
              <span className="font-mono font-bold text-amber-400">
                {(item.similarity_score * 100).toFixed(0)}%
              </span>
            </div>
          )}
        </div>

        {/* Conflict / Flag Reasons */}
        <div className="p-4 rounded-xl bg-amber-500/5 border border-amber-500/20 text-amber-300 space-y-1.5">
          <div className="flex items-center gap-1.5 font-semibold text-amber-200">
            <ShieldAlert className="w-4 h-4 text-amber-400" />
            <span>Matching Evidence & Hard-Conflict Flags</span>
          </div>
          <ul className="list-disc pl-5 space-y-1 text-slate-300">
            {item.reasons.map((r, i) => (
              <li key={i}>{r}</li>
            ))}
          </ul>
        </div>

        {/* Action Selection */}
        <div>
          <label className="block text-slate-300 font-semibold mb-2">Triage Decision</label>
          <div className="grid grid-cols-3 gap-2">
            <button
              type="button"
              disabled={hasHardConflicts}
              onClick={() => setSelectedAction('APPROVED')}
              className={`p-3 rounded-xl border text-center transition-all flex flex-col items-center gap-1.5 ${
                selectedAction === 'APPROVED'
                  ? 'border-emerald-500 bg-emerald-500/10 text-emerald-300 shadow-sm'
                  : 'border-[#1C283F] bg-[#0D1423] text-slate-400 hover:border-slate-700 disabled:opacity-40 disabled:cursor-not-allowed'
              }`}
            >
              <CheckCircle2 className="w-5 h-5 text-emerald-400" />
              <span className="font-medium">Approve Merge</span>
            </button>

            <button
              type="button"
              onClick={() => setSelectedAction('REJECTED')}
              className={`p-3 rounded-xl border text-center transition-all flex flex-col items-center gap-1.5 ${
                selectedAction === 'REJECTED'
                  ? 'border-rose-500 bg-rose-500/10 text-rose-300 shadow-sm'
                  : 'border-[#1C283F] bg-[#0D1423] text-slate-400 hover:border-slate-700'
              }`}
            >
              <XCircle className="w-5 h-5 text-rose-400" />
              <span className="font-medium">Reject Match</span>
            </button>

            <button
              type="button"
              onClick={() => setSelectedAction('RESOLVED')}
              className={`p-3 rounded-xl border text-center transition-all flex flex-col items-center gap-1.5 ${
                selectedAction === 'RESOLVED'
                  ? 'border-cyan-500 bg-cyan-500/10 text-cyan-300 shadow-sm'
                  : 'border-[#1C283F] bg-[#0D1423] text-slate-400 hover:border-slate-700'
              }`}
            >
              <AlertOctagon className="w-5 h-5 text-cyan-400" />
              <span className="font-medium">Mark Distinct</span>
            </button>
          </div>
          {hasHardConflicts && (
            <p className="mt-1.5 text-[10px] text-amber-400">
              * Merge approval is safely locked due to conflicting unique identifier safeguards.
            </p>
          )}
        </div>

        {/* Steward Notes */}
        <div>
          <label className="block text-slate-300 font-semibold mb-1">Audit Notes (Optional)</label>
          <textarea
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder="Document reason for steward decision..."
            rows={2}
            className="w-full px-3 py-2 rounded-xl bg-[#0D1423] border border-[#1C283F] text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-500/40 font-sans"
          />
        </div>

        {error && (
          <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-300">
            {error}
          </div>
        )}

        {/* Buttons */}
        <div className="flex justify-end gap-2 pt-2 border-t border-[#1C283F]">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 rounded-lg border border-[#1C283F] text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
          >
            Cancel
          </button>
          <button
            type="button"
            disabled={submitting}
            onClick={handleSubmit}
            className="px-5 py-2 rounded-lg bg-cyan-500 text-slate-950 font-semibold hover:bg-cyan-400 transition-colors shadow-glow disabled:opacity-50"
          >
            {submitting ? 'Updating...' : 'Confirm Decision'}
          </button>
        </div>
      </div>
    </Modal>
  );
};

