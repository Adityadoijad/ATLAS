import { useEffect, useRef, useState } from 'react';
import { MapPinIcon, XIcon } from 'lucide-react';
import { LocationSuggestion } from '../../types';
import { searchLocations } from '../../services/atlasApi';
import { Input } from '../ui/Primitives';
import { cn } from '../../utils/format';

/**
 * Where the traveller's journey begins — a station, an airport, an address.
 *
 * The user picks a real, geocoded place rather than typing free text, because
 * this becomes the origin of the itinerary's first route leg. A typo that
 * silently resolved to the wrong city would put a wrong distance on every
 * subsequent screen.
 *
 * Suggestions come through ATLAS's own endpoint, never straight to Nominatim:
 * that keeps one User-Agent and one rate limiter in front of the geocoder,
 * which its usage policy requires. The debounce is part of that contract, not
 * just a UX nicety.
 */

const DEBOUNCE_MS = 450;
const MIN_QUERY_LENGTH = 3;

export function BoardingLocationField({
  value,
  onChange,
  error
}: {
  value: LocationSuggestion | null;
  onChange: (next: LocationSuggestion | null) => void;
  error?: string;
}) {
  const [query, setQuery] = useState(value?.displayName ?? '');
  const [suggestions, setSuggestions] = useState<LocationSuggestion[]>([]);
  const [status, setStatus] = useState<'idle' | 'searching' | 'empty' | 'failed'>('idle');
  const [open, setOpen] = useState(false);
  // Guards against a slow earlier request overwriting a newer one's results.
  const requestId = useRef(0);

  useEffect(() => {
    // A confirmed selection is not a search term; re-querying it would reopen
    // the list over the answer the user already gave.
    if (value && query === value.displayName) {
      setSuggestions([]);
      setStatus('idle');
      return;
    }
    if (query.trim().length < MIN_QUERY_LENGTH) {
      setSuggestions([]);
      setStatus('idle');
      return;
    }

    const token = localStorage.getItem('atlas_access_token');
    if (!token) {
      setStatus('failed');
      return;
    }

    const id = ++requestId.current;
    setStatus('searching');
    const timer = setTimeout(() => {
      searchLocations(query.trim(), token).
      then((results) => {
        if (id !== requestId.current) return;
        setSuggestions(results);
        setStatus(results.length === 0 ? 'empty' : 'idle');
        setOpen(true);
      }).
      catch(() => {
        if (id !== requestId.current) return;
        setSuggestions([]);
        setStatus('failed');
      });
    }, DEBOUNCE_MS);

    return () => clearTimeout(timer);
  }, [query, value]);

  const select = (suggestion: LocationSuggestion) => {
    onChange(suggestion);
    setQuery(suggestion.displayName);
    setSuggestions([]);
    setOpen(false);
    setStatus('idle');
  };

  const clear = () => {
    onChange(null);
    setQuery('');
    setSuggestions([]);
    setStatus('idle');
  };

  return (
    <div className="relative">
      <div className="relative">
        <Input
          id="boarding-location"
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            // Editing the text invalidates the confirmed place: the field must
            // not keep submitting a location the box no longer shows.
            if (value) onChange(null);
          }}
          onFocus={() => suggestions.length > 0 && setOpen(true)}
          placeholder="e.g. Nagpur Railway Station"
          autoComplete="off"
          aria-describedby="boarding-location-help"
          aria-expanded={open}
          aria-autocomplete="list" />

        {query &&
        <button
          type="button"
          onClick={clear}
          aria-label="Clear starting location"
          className="absolute right-2.5 top-1/2 -translate-y-1/2 rounded-lg p-1 text-muted transition-colors hover:bg-subtle hover:text-ink">

            <XIcon className="h-3.5 w-3.5" />
          </button>
        }
      </div>

      <p id="boarding-location-help" className="mt-1.5 text-[12px] text-muted">
        {value ?
        'Your itinerary will start here.' :
        'Pick a suggestion so ATLAS can route the first leg of your trip.'}
      </p>

      {status === 'searching' && query.trim().length >= MIN_QUERY_LENGTH &&
      <p className="mt-1 text-[12px] text-muted">Searching…</p>
      }
      {status === 'empty' &&
      <p className="mt-1 text-[12px] text-muted">
          No matching place found. Try a station, airport or full address.
        </p>
      }
      {status === 'failed' &&
      <p className="mt-1 text-[12px] text-muted">
          The location service is unavailable right now. Please try again shortly.
        </p>
      }

      {open && suggestions.length > 0 &&
      <ul
        className="absolute z-20 mt-1 max-h-64 w-full overflow-auto rounded-xl border border-line bg-surface shadow-lg"
        role="listbox"
        aria-label="Starting location suggestions">

          {suggestions.map((suggestion) =>
        <li key={`${suggestion.latitude},${suggestion.longitude}`}>
              <button
            type="button"
            onClick={() => select(suggestion)}
            className={cn(
              'flex w-full items-start gap-2 px-3 py-2.5 text-left text-[13px] transition-colors',
              'hover:bg-canvas focus-visible:bg-canvas focus-visible:outline-none'
            )}>

                <MapPinIcon className="mt-0.5 h-3.5 w-3.5 shrink-0 text-brand" />
                <span className="min-w-0">
                  <span className="block font-semibold text-ink">{suggestion.name}</span>
                  <span className="block text-[12px] leading-snug text-muted">{suggestion.displayName}</span>
                </span>
              </button>
            </li>
        )}
        </ul>
      }

      {error && <p className="mt-1.5 text-[12.5px] text-danger">{error}</p>}
    </div>);

}
