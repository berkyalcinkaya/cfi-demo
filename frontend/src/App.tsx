import {
  BrowserRouter,
  Routes,
  Route,
  Navigate,
  Outlet,
  useLocation,
} from 'react-router'
import { AppShell } from './components/AppShell'
import { auth } from './lib/api'
import Login from './pages/Login'
import PatientOverview from './pages/PatientOverview'
import FocalScroll from './pages/FocalScroll'
import Timeline from './pages/Timeline'
import Comparison from './pages/Comparison'
import Admin from './pages/Admin'

// Layout route: redirects unauthenticated users to /login, otherwise renders the
// app shell around the matched child route.
function ProtectedLayout() {
  const location = useLocation()
  if (!auth.isAuthed()) {
    return <Navigate to="/login" replace state={{ from: location }} />
  }
  return (
    <AppShell>
      <Outlet />
    </AppShell>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route element={<ProtectedLayout />}>
          <Route
            path="/"
            element={<Navigate to="/patients/patient1" replace />}
          />
          <Route path="/patients/:patientId" element={<PatientOverview />} />
          <Route
            path="/patients/:patientId/compare"
            element={<Comparison />}
          />
          <Route
            path="/patients/:patientId/embryos/:embryoLabel/timepoints/:timepoint"
            element={<FocalScroll />}
          />
          <Route
            path="/patients/:patientId/embryos/:embryoLabel/timeline"
            element={<Timeline />}
          />
          <Route path="/admin" element={<Admin />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
