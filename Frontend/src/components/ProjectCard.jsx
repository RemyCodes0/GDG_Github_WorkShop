import { useId } from 'react'
import CategoryBadge from './CategoryBadge'
import './ProjectCard.css'

const statusStyles = {
  Draft: 'draft',
  Recruiting: 'recruiting',
  Active: 'active',
  Completed: 'completed',
  Archived: 'archived',
}

/**
 * A presentational project summary. All fields are plain text; skills is a
 * string array. Supply href only when a real project details URL is available.
 */
export default function ProjectCard({
  title,
  description,
  category,
  skills = [],
  duration,
  status,
  href,
}) {
  const headingId = useId()
  const projectTitle = title?.trim() || 'Untitled project'
  const projectCategory = category?.trim() || 'Uncategorized'
  const projectStatus = status?.trim() || 'Status not specified'
  const projectSkills = [...new Set((skills ?? []).map((skill) => skill.trim()).filter(Boolean))]

  return (
    <article className="project-card" aria-labelledby={headingId}>
      <div className="project-card__labels">
        <span className="project-card__category"><CategoryBadge category={projectCategory} /></span>
        <span className={`project-card__status project-card__status--${statusStyles[projectStatus] || 'unknown'}`}>
          {projectStatus}
        </span>
      </div>

      <h2 id={headingId} className="project-card__title">
        {href ? <a href={href}>{projectTitle}</a> : projectTitle}
      </h2>
      <p className="project-card__description">
        {description?.trim() || 'No description provided yet.'}
      </p>

      <div className="project-card__skills">
        <p className="project-card__label">Skills</p>
        {projectSkills.length ? (
          <ul aria-label="Project skills">
            {projectSkills.map((skill) => <li key={skill}>{skill}</li>)}
          </ul>
        ) : (
          <p className="project-card__empty">No specific skills listed.</p>
        )}
      </div>

      <dl className="project-card__duration">
        <dt>Duration</dt>
        <dd>{duration?.trim() || 'Not specified'}</dd>
      </dl>
    </article>
  )
}
