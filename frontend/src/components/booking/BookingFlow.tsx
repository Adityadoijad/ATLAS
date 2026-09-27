import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { AlertTriangleIcon, CheckCircle2Icon, DownloadIcon, MailIcon, QrCodeIcon } from 'lucide-react';
import { Modal } from '../ui/Overlays';
import { Button, Field, Input, Select } from '../ui/Primitives';
import {
  createBooking,
  downloadBookingTicket,
  emailBookingConfirmation,
  fetchEmailCapability } from
'../../services/atlasApi';
import { useAtlas } from '../../contexts/AtlasContext';
import { Booking } from '../../types';
import { cn, formatDate, inr } from '../../utils/format';

/**
 * The existing booking data model. Exported so other surfaces (the Assistant's
 * booking hand-off) can prefill this flow instead of defining a second
 * booking shape.
 */
export interface BookingInput {
  title: string;
  type: Booking['type'];
  date: string;
  price: number;
  travelers: number;
  image?: string;
  /** Links the booking to a persisted trip so the e-ticket can print its itinerary. */
  tripId?: string;
}

const stepLabels = ['Review booking', 'Traveller details', 'Summary', 'Simulation complete'];

function QrPlaceholder({ reference }: {reference: string;}) {
  const cells = Array.from({ length: 64 }).map((_, i) => (reference.charCodeAt(i % reference.length) + i) % 3 === 0);
  return (
    <div className="mx-auto grid h-32 w-32 grid-cols-8 gap-0.5 rounded-xl bg-white p-2" aria-label={`QR code for booking ${reference}`} role="img">
      {cells.map((filled, i) =>
      <span key={i} className={cn('rounded-[1px]', filled ? 'bg-slate-900' : 'bg-white')} />
      )}
    </div>);

}

export function BookingFlow({
  open,
  onClose,
  item




}: {open: boolean;onClose: () => void;item: BookingInput;}) {
  const [step, setStep] = useState(0);
  const { addBooking, toast, authUser } = useAtlas();
  const [name, setName] = useState(authUser?.name ?? '');
  const [email, setEmail] = useState(authUser?.email ?? '');
  const [phone, setPhone] = useState('');
  const [idType, setIdType] = useState('Passport');
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(false);
  const [booking, setBooking] = useState<Booking | null>(null);
  const [downloading, setDownloading] = useState(false);
  // Email state is tracked separately from the booking on purpose: a failed
  // send must never read as a failed booking.
  const [emailState, setEmailState] = useState<'idle' | 'sending' | 'sent' | 'failed'>('idle');
  const [emailMessage, setEmailMessage] = useState('');
  const [emailAvailable, setEmailAvailable] = useState(false);

  useEffect(() => {
    const token = localStorage.getItem('atlas_access_token');
    if (!open || !token) return;
    // Asked once per opening so the action is hidden entirely on a deployment
    // with no mail configured.
    fetchEmailCapability(token).then(setEmailAvailable);
  }, [open]);

  const close = () => {
    onClose();
    window.setTimeout(() => {
      setStep(0);
      setBooking(null);
      setEmailState('idle');
      setEmailMessage('');
    }, 250);
  };

  const validateDetails = () => {
    const next: Record<string, string> = {};
    if (!name.trim()) next.name = 'Enter the lead traveller name.';
    if (!/^\S+@\S+\.\S+$/.test(email)) next.email = 'Enter a valid email address.';
    if (phone.replace(/\D/g, '').length < 10) next.phone = 'Enter a valid phone number.';
    setErrors(next);
    return Object.keys(next).length === 0;
  };

  const confirm = async () => {
    setLoading(true);
    try {
      const created = await createBooking({
        ...item,
        // Captured here so the e-ticket can name the lead traveller instead of
        // leaving the section blank.
        leadTravelerName: name.trim(),
        leadTravelerEmail: email.trim(),
        leadTravelerPhone: phone.trim(),
        idDocumentType: idType
      });
      addBooking(created);
      setBooking(created);
      setStep(3);
      toast({ title: 'Booking simulation saved', description: `Reference ${created.reference} — no real reservation was made.`, tone: 'success' });
    } catch (reason) {
      toast({
        title: 'Could not save the booking',
        description: reason instanceof Error ? reason.message : 'Please try again.',
        tone: 'error'
      });
    } finally {
      setLoading(false);
    }
  };

  const sendConfirmationEmail = async () => {
    const token = localStorage.getItem('atlas_access_token');
    if (!booking || !token) return;
    setEmailState('sending');
    try {
      const result = await emailBookingConfirmation(booking.id, token);
      setEmailState('sent');
      setEmailMessage(result.recipient);
    } catch (reason) {
      // Only the email failed. The booking above stays confirmed and the PDF
      // stays downloadable, so this is reported as its own status rather than
      // as an error on the booking.
      setEmailState('failed');
      setEmailMessage(reason instanceof Error ? reason.message : 'The confirmation email could not be sent.');
    }
  };

  const downloadTicket = async () => {
    const token = localStorage.getItem('atlas_access_token');
    if (!booking || !token) return;
    setDownloading(true);
    try {
      await downloadBookingTicket(booking.id, token);
    } catch (reason) {
      toast({
        title: 'Could not generate the E-Ticket',
        description: reason instanceof Error ? reason.message : 'Please try again.',
        tone: 'error'
      });
    } finally {
      setDownloading(false);
    }
  };

  return (
    <Modal
      open={open}
      onClose={close}
      size="lg"
      title={stepLabels[step]}
      description={step < 3 ? 'Demonstration booking — no payment is processed.' : undefined}
      footer={
      step === 0 ?
      <>
            <Button variant="ghost" onClick={close}>
              Cancel
            </Button>
            <Button onClick={() => setStep(1)}>Continue</Button>
          </> :
      step === 1 ?
      <>
            <Button variant="ghost" onClick={() => setStep(0)}>
              Back
            </Button>
            <Button onClick={() => validateDetails() && setStep(2)}>Review summary</Button>
          </> :
      step === 2 ?
      <>
            <Button variant="ghost" onClick={() => setStep(1)}>
              Back
            </Button>
            <Button loading={loading} onClick={confirm}>
              Confirm booking
            </Button>
          </> :

      <>
            {/* Only offered for a persisted booking — a signed-out demo
                booking has no server record to issue a ticket from. */}
            {booking?.persisted &&
        <Button
          variant="secondary"
          loading={downloading}
          icon={<DownloadIcon className="h-4 w-4" />}
          onClick={downloadTicket}>

                Download E-Ticket PDF
              </Button>
        }
            <Button onClick={close}>Done</Button>
          </>

      }>
      
      <div className="mb-5 flex items-center gap-2">
        {stepLabels.map((label, i) =>
        <div key={label} className="flex flex-1 items-center gap-2">
            <span
            className={cn(
              'h-1.5 flex-1 rounded-full transition-colors',
              i <= step ? 'bg-brand' : 'bg-subtle'
            )} />
          
          </div>
        )}
      </div>

      {step === 0 &&
      <div className="space-y-4">
          <div className="flex items-center gap-4 rounded-2xl border border-line p-4">
            {item.image && <img src={item.image} alt="" className="h-16 w-20 rounded-xl object-cover" />}
            <div>
              <p className="text-[15px] font-bold text-ink">{item.title}</p>
              <p className="text-[13px] text-muted">
                {item.type} · {formatDate(item.date)} · {item.travelers} traveller{item.travelers > 1 ? 's' : ''}
              </p>
            </div>
          </div>
          <dl className="divide-y divide-line rounded-2xl border border-line text-[13.5px]">
            <div className="flex justify-between px-4 py-3">
              <dt className="text-muted">Base price</dt>
              <dd className="font-semibold text-ink">{inr(Math.round(item.price * 0.88))}</dd>
            </div>
            <div className="flex justify-between px-4 py-3">
              <dt className="text-muted">Taxes & fees</dt>
              <dd className="font-semibold text-ink">{inr(Math.round(item.price * 0.12))}</dd>
            </div>
            <div className="flex justify-between px-4 py-3">
              <dt className="font-semibold text-ink">Total</dt>
              <dd className="text-base font-bold text-brand">{inr(item.price)}</dd>
            </div>
          </dl>
        </div>
      }

      {step === 1 &&
      <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Lead traveller name" error={errors.name} htmlFor="bk-name">
            <Input id="bk-name" value={name} onChange={(e) => setName(e.target.value)} />
          </Field>
          <Field label="Email address" error={errors.email} htmlFor="bk-email">
            <Input id="bk-email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} />
          </Field>
          <Field label="Phone number" error={errors.phone} htmlFor="bk-phone">
            <Input id="bk-phone" value={phone} onChange={(e) => setPhone(e.target.value)} />
          </Field>
          <Field label="ID document" htmlFor="bk-id">
            <Select id="bk-id" value={idType} onChange={(e) => setIdType(e.target.value)}>
              <option>Passport</option>
              <option>Aadhaar</option>
              <option>Driving licence</option>
            </Select>
          </Field>
        </div>
      }

      {step === 2 &&
      <dl className="divide-y divide-line rounded-2xl border border-line text-[13.5px]">
          {[
        ['Item', item.title],
        ['Type', item.type],
        ['Date', formatDate(item.date)],
        ['Travellers', String(item.travelers)],
        ['Lead traveller', name],
        ['Contact', `${email} · ${phone}`],
        ['ID document', idType],
        ['Total payable', inr(item.price)]].
        map(([label, value]) =>
        <div key={label} className="flex justify-between gap-6 px-4 py-3">
              <dt className="text-muted">{label}</dt>
              <dd className="text-right font-semibold text-ink">{value}</dd>
            </div>
        )}
        </dl>
      }

      {step === 3 && booking &&
      <motion.div initial={{ opacity: 0, scale: 0.97 }} animate={{ opacity: 1, scale: 1 }} className="text-center">
          <span className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-success/10 text-success">
            <CheckCircle2Icon className="h-7 w-7" />
          </span>
          <h3 className="mt-4 text-xl font-bold text-ink">Booking simulation complete</h3>
          <p className="mt-1 text-[13.5px] text-muted">{item.title}</p>
          <p className="mx-auto mt-3 max-w-sm rounded-xl border border-warning/30 bg-warning/10 px-3 py-2 text-[12.5px] font-medium text-[#92400E] dark:text-warning">
            This is a booking simulation — no real reservation has been made and no payment was processed.
          </p>
          <div className="mt-6 rounded-2xl border border-line bg-canvas p-5">
            <QrPlaceholder reference={booking.reference} />
            <p className="mt-4 flex items-center justify-center gap-1.5 font-mono text-[13px] font-semibold text-ink">
              <QrCodeIcon className="h-3.5 w-3.5" /> {booking.reference}
            </p>
            <p className="mt-1 text-[12.5px] text-muted">Simulated reference · {formatDate(booking.date)}</p>
          </div>

          {/* Email status, reported separately from the booking above so a
              delivery failure never reads as a booking failure. */}
          {booking.persisted && emailAvailable &&
        <div className="mt-5 text-left">
              {emailState === 'sent' ?
          <p className="flex items-start gap-2 rounded-xl border border-success/30 bg-success/10 px-3.5 py-3 text-[13px] font-medium text-success">
                  <CheckCircle2Icon className="mt-0.5 h-4 w-4 shrink-0" />
                  <span>Confirmation email sent to your registered address ({emailMessage}).</span>
                </p> :
          emailState === 'failed' ?
          <div className="rounded-xl border border-warning/30 bg-warning/10 px-3.5 py-3">
                  <p className="flex items-start gap-2 text-[13px] font-semibold text-[#92400E] dark:text-warning">
                    <AlertTriangleIcon className="mt-0.5 h-4 w-4 shrink-0" />
                    <span>Confirmation email could not be sent.</span>
                  </p>
                  <p className="mt-1 pl-6 text-[12.5px] text-[#92400E] dark:text-warning">
                    Your booking is still confirmed — download the PDF instead.
                  </p>
                  <Button
              className="ml-6 mt-2.5"
              size="sm"
              variant="outline"
              onClick={sendConfirmationEmail}>

                    Try again
                  </Button>
                </div> :

          <Button
            variant="outline"
            size="sm"
            loading={emailState === 'sending'}
            icon={<MailIcon className="h-4 w-4" />}
            onClick={sendConfirmationEmail}>

                  Email Confirmation
                </Button>
          }
            </div>
        }
        </motion.div>
      }
    </Modal>);

}
