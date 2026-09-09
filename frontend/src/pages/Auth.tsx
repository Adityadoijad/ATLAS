import { useState } from 'react';
import { Navigate, useLocation, useNavigate } from 'react-router-dom';
import { Button, Card, Field, Input } from '../components/ui/Primitives';
import { useAtlas } from '../contexts/AtlasContext';
import { getGoogleAuthUrl } from '../services/atlasApi';

export function AuthPage() {
  const { authUser, login, register } = useAtlas();
  const navigate = useNavigate();
  const location = useLocation();
  const [isRegistering, setIsRegistering] = useState(location.pathname === '/register');
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  if (authUser) return <Navigate to="/dashboard" replace />;

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    setLoading(true);
    setError('');
    try {
      if (isRegistering) await register(name, email, password);
      else await login(email, password);
      navigate('/dashboard', { replace: true });
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Authentication failed.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="mx-auto max-w-md py-12">
      <Card className="p-6 sm:p-8">
        <h1 className="font-display text-3xl font-bold text-ink">{isRegistering ? 'Create your ATLAS account' : 'Welcome back'}</h1>
        <p className="mt-2 text-sm text-muted">Your trips and saved places stay synced across sessions.</p>
        <form className="mt-6 space-y-4" onSubmit={submit}>
          {isRegistering && <Field label="Name" htmlFor="auth-name"><Input id="auth-name" required value={name} onChange={(event) => setName(event.target.value)} /></Field>}
          <Field label="Email" htmlFor="auth-email"><Input id="auth-email" required type="email" value={email} onChange={(event) => setEmail(event.target.value)} /></Field>
          <Field label="Password" htmlFor="auth-password"><Input id="auth-password" required minLength={8} type="password" value={password} onChange={(event) => setPassword(event.target.value)} /></Field>
          {error && <p className="text-sm text-danger" role="alert">{error}</p>}
          <Button type="submit" loading={loading} className="w-full">{isRegistering ? 'Register' : 'Log in'}</Button>
        </form>
        <button className="mt-5 text-sm font-semibold text-brand" onClick={() => setIsRegistering((value) => !value)}>
          {isRegistering ? 'Already have an account? Log in' : 'Need an account? Register'}
        </button>

        <div className="relative my-6">
          <div className="absolute inset-0 flex items-center">
            <div className="w-full border-t border-muted-200"></div>
          </div>
          <div className="relative flex justify-center text-sm">
            <span className="bg-paper px-2 text-muted">or continue with</span>
          </div>
        </div>

        <Button
          type="button"
          variant="outline"
          className="w-full flex items-center justify-center gap-2"
          onClick={() => window.location.href = getGoogleAuthUrl()}
        >
          <svg className="h-5 w-5" viewBox="0 0 24 24">
            <path
              d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
              fill="#4285F4"
            />
            <path
              d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
              fill="#34A853"
            />
            <path
              d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
              fill="#FBBC05"
            />
            <path
              d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
              fill="#EA4335"
            />
          </svg>
          Continue with Google
        </Button>
      </Card>
    </div>
  );
}
