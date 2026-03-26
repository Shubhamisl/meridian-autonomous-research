# Milestone 1: Firebase Auth & Masonry UI Redesign

## Goal
Add Firebase Authentication and completely redesign the frontend into a Pinterest-style masonry grid of glassmorphic post cards.

## Authentication

### Frontend (React)
- New `/login` route with a dedicated Login page component.
- Firebase JS SDK (`firebase/auth`) for Google Sign-In (popup flow).
- `AuthContext` provider wrapping the app to manage user state.
- Protected route wrapper redirecting unauthenticated users to `/login`.
- Attach Firebase ID token as `Authorization: Bearer <token>` on every API call.

### Backend (FastAPI)
- `firebase-admin` SDK initialized with service account credentials.
- `get_current_user` dependency that extracts and verifies the Bearer token.
- All `/research/*` endpoints protected behind this dependency.
- Research jobs linked to the authenticated `user_id` from the token.

## UI Redesign

### Layout
- **Header**: Compact nav bar with logo, search input, and user avatar/logout.
- **Masonry Grid**: `react-masonry-css` for a responsive Pinterest-style card layout below the header.
- **Post Cards**: Glassmorphic cards with variable height showing: title (query), status badge, snippet of report, timestamp, and action buttons (view, download, share).

### Design System
- Retain dark ambient aesthetic with tightened card borders and improved typography.
- Use Stitch MCP to generate high-fidelity screen designs for Login and Dashboard pages.

### New Pages/Components
| Component | Purpose |
|---|---|
| `LoginPage.tsx` | Firebase Google Sign-In UI |
| `AuthContext.tsx` | React context for auth state |
| `ProtectedRoute.tsx` | Route guard component |
| `MasonryDashboard.tsx` | Masonry grid layout replacing old Dashboard |
| `ResearchCard.tsx` | Individual post card in the grid |
| `Navbar.tsx` | Top navigation with search + user menu |

## Data Flow
```
User logs in (Firebase) → JWT token stored in React state
↓
User submits query → POST /research (Bearer token attached)
↓
FastAPI verifies token → creates job linked to user_id
↓
Celery processes job → stores report
↓
Frontend polls GET /research/{id} → renders card in masonry grid
```
