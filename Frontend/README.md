# AUB Collab — Frontend

The web client for **AUB Collab**, the AUB student collaboration platform where students post project ideas, discover projects that match their skills, and apply to join teams.

> *Have an idea. Find your people. Build it together.*

For the full project vision, see the [root README](../README.md). The API this app talks to lives in [`../Backend`](../Backend).

## Tech Stack

* [React](https://react.dev) 19
* [Vite](https://vite.dev) for dev server and bundling
* [oxlint](https://oxc.rs/docs/guide/usage/linter) for linting

## Getting Started

Requires Node.js 20 or newer.

```bash
npm install
npm run dev
```

The app runs at http://localhost:5173. The backend is expected at http://localhost:8000.

## Scripts

| Command | Description |
| --- | --- |
| `npm run dev` | Start the dev server with hot reload |
| `npm run build` | Create a production build in `dist/` |
| `npm run preview` | Preview the production build locally |
| `npm test` | Test Project Card rendering and fallback behavior |
| `npm run lint` | Lint the codebase |

## Project Card

Open `/project-card.html` on the development or preview server to see three
sample cards. This separate component preview leaves the existing homepage intact.
The preview grid adapts to narrow screens; the card also inherits the app's light
and dark theme variables. Long text and skill labels wrap without truncation.

```jsx
import ProjectCard from './components/ProjectCard'

<ProjectCard
  title="AI-Powered Campus Navigation"
  description="Build an accessible campus navigation tool."
  category="Technology"
  skills={['React', 'Python', 'UI/UX design']}
  duration="3 months"
  status="Recruiting"
/>
```

All fields are strings except `skills`, which is an array of strings. Missing or
blank fields have readable fallbacks. Blank/duplicate skills are omitted.
The existing `CategoryBadge` supplies category colors. Status is always expressed
as text, including unknown statuses. An optional `href` turns the title into a
keyboard-accessible details link; omit it until the destination exists.

Each card is an `article` labelled by its `h2`. Place cards below the page's `h1`.
Run `npm test`, `npm run lint`, and `npm run build` before submitting changes.

## What This App Will Do

* **Create projects:** title, description, goals, category, duration, time commitment, required majors and skills, collaborators needed, deadline, and difficulty.
* **Discover projects:** browse, search, and filter by interest, major, skills, availability, and type of collaboration.
* **Apply to projects:** submit a CV, major and year, skills, experience, links (GitHub, portfolio, LinkedIn), motivation, and availability.
* **Manage applications:** project creators review applicants and pick their team.
* **Profiles and portfolios:** show skills through real project contributions.
* **Recommendations:** personalized matches such as "92% Match".
* **Team workspaces (later):** tasks, milestones, discussions, resources, and progress.

## Contributing

AUB Collab is open source and built by students. Frontend issues are labeled by difficulty:

* **Easy:** UI components, frontend improvements, documentation, testing, accessibility, bug fixes, form validation
* **Medium:** search and filtering, profile pages, application management UI, notifications
* **Hard:** real-time collaboration, recommendation and matching UI, performance optimization

Before opening a pull request, run `npm run lint` and `npm run build`.
