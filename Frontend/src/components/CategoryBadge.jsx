import './CategoryBadge.css';

function CategoryBadge({ category }) {
  const slug = category.toLowerCase().replace(/\s+/g, '-');
  return <span className={`category-badge category-badge--${slug}`}>{category}</span>;
}

export default CategoryBadge;