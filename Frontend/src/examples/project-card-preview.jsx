import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import ProjectCard from '../components/ProjectCard'
import '../index.css'
import './project-card-preview.css'

const projects = [
  {
    title: 'AI-Powered Campus Navigation',
    description: 'Help students find accessible routes around campus. Bring your engineering, design, or research skills to a student-built navigation tool.',
    category: 'Technology',
    skills: ['React', 'Python', 'UI/UX design'],
    duration: '3 months',
    status: 'Recruiting',
  },
  {
    title: 'Turning food waste into a campus-wide opportunity',
    description: 'Work across disciplines to understand food waste and design a practical reduction program for the AUB community.',
    category: 'Social Impact',
    skills: ['Research', 'Data analysis', 'Community outreach'],
    duration: '6 weeks',
    status: 'Active',
  },
  {
    title: 'Student oral history archive',
    description: 'Preserve student stories and make them available to future generations.',
    category: 'Research',
    skills: [],
    status: 'Completed',
  },
]

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <main className="project-card-preview">
      <header>
        <p className="project-card-preview__eyebrow">AUB Collab · Component preview</p>
        <h1>Ideas worth building together.</h1>
        <p>Sample projects demonstrating the reusable Project Card.</p>
      </header>
      <section className="project-card-preview__grid" aria-label="Sample projects">
        {projects.map((project) => <ProjectCard key={project.title} {...project} />)}
      </section>
    </main>
  </StrictMode>,
)
