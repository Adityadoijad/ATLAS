import { useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useAtlas } from '../contexts/AtlasContext';
import { Card } from '../components/ui/Primitives';
import { Loader2, AlertCircle } from 'lucide-react';

export function AuthCallbackPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { initializeSession, toast } = useAtlas();

  const token = searchParams.get('token');
  const error = searchParams.get('error');

  useEffect(() => {
    if (error) {
      toast({ title: 'Authentication failed', description: error, tone: 'error' });
      navigate('/login', { replace: true });
      return;
    }

    if (!token) {
      toast({ title: 'Authentication failed', description: 'No token received from Google.', tone: 'error' });
      navigate('/login', { replace: true });
      return;
    }

    // Initialize session with the token
    initializeSession(token)
      .then(() => {
        toast({ title: 'Welcome to ATLAS!', description: 'You have been signed in with Google.', tone: 'success' });
        navigate('/dashboard', { replace: true });
      })
      .catch((err) => {
        toast({ title: 'Authentication failed', description: err instanceof Error ? err.message : 'Could not complete sign-in.', tone: 'error' });
        navigate('/login', { replace: true });
      });
  }, [token, error, initializeSession, navigate, toast]);

  return (
    <div className="mx-auto max-w-md py-12 flex items-center justify-center min-h-[60vh]">
      <Card className="p-8 text-center">
        {error ? (
          <>
            <AlertCircle className="mx-auto h-12 w-12 text-danger" />
            <h2 className="mt-4 text-lg font-semibold text-ink">Authentication Error</h2>
            <p className="mt-2 text-sm text-muted">{error}</p>
            <a href="/login" className="mt-6 inline-block text-sm font-semibold text-brand underline">
              Try again
            </a>
          </>
        ) : (
          <>
            <Loader2 className="mx-auto h-12 w-12 text-brand animate-spin" />
            <h2 className="mt-4 text-lg font-semibold text-ink">Completing sign-in…</h2>
            <p className="mt-2 text-sm text-muted">Redirecting you to your dashboard</p>
          </>
        )}
      </Card>
    </div>
  );
}
