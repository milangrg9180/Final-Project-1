# utils/recommendations.py - Recommendation algorithms
from .database import get_db

def get_recommendations(user_id):
    """Get personalized internship recommendations for a user."""
    conn = get_db()
    cursor = conn.cursor()
    
    # Content-based recommendations (enhanced with CV data)
    content_recs = content_based_recommendations(user_id, cursor)
    
    # CV-based recommendations
    cv_recs = cv_based_recommendations(user_id, cursor)
    
    # Collaborative filtering recommendations
    collab_recs = collaborative_filtering(user_id, cursor)
    
    # Combine and deduplicate recommendations
    all_recs = {rec['id']: rec for rec in content_recs}
    for rec in cv_recs:
        if rec['id'] not in all_recs:
            all_recs[rec['id']] = rec
        else:
            # If CV recommendation has higher similarity, use it
            if rec['similarity'] > all_recs[rec['id']]['similarity']:
                all_recs[rec['id']] = rec
    
    for rec in collab_recs:
        if rec['id'] not in all_recs:
            all_recs[rec['id']] = rec
    
    return list(all_recs.values())

def content_based_recommendations(user_id, cursor):
    """Content-based recommendation algorithm using skill matching."""
    # Get student's skills
    cursor.execute("SELECT skills FROM profiles WHERE user_id=?", (user_id,))
    profile = cursor.fetchone()
    
    if not profile or not profile['skills']:
        return []
    
    student_skills = set(skill.strip().lower() for skill in profile['skills'].split(','))
    
    # Get all internships
    cursor.execute("SELECT * FROM internships")
    internships = cursor.fetchall()
    
    # Calculate similarity for each internship
    recommendations = []
    for internship in internships:
        required_skills = set(skill.strip().lower() for skill in internship['required_skills'].split(',')) if internship['required_skills'] else set()
        
        if not required_skills:
            continue
            
        # Jaccard similarity
        intersection = len(student_skills & required_skills)
        union = len(student_skills | required_skills)
        similarity = intersection / union if union > 0 else 0
        
        if similarity > 0.2:  # Threshold
            # Get company information
            cursor.execute("SELECT name FROM users WHERE id=?", (internship['company_id'],))
            company = cursor.fetchone()
            company_name = company['name'] if company else 'Unknown Company'
            
            recommendations.append({
                'id': internship['id'],
                'title': internship['title'],
                'description': internship['description'],
                'required_skills': internship['required_skills'],
                'posted_at': internship['posted_at'],
                'company_name': company_name,
                'company_id': internship['company_id'],
                'similarity': similarity,
                'type': 'Content-based'
            })
    
    # Sort by similarity
    recommendations.sort(key=lambda x: x['similarity'], reverse=True)
    return recommendations[:5]  # Top 5

def cv_based_recommendations(user_id, cursor):
    """CV-based recommendation algorithm using comprehensive CV data."""
    # Get student's CV
    cursor.execute("SELECT * FROM cvs WHERE user_id=?", (user_id,))
    cv = cursor.fetchone()
    
    if not cv:
        return []
    
    # Extract skills and experience from CV
    cv_skills = set()
    cv_experience = set()
    
    # Extract skills from certifications field
    if cv['certifications']:
        cert_text = cv['certifications'].lower()
        # Common technical skills to look for
        tech_skills = ['python', 'java', 'javascript', 'react', 'node', 'sql', 'html', 'css', 
                      'flask', 'django', 'machine learning', 'data science', 'web development',
                      'mobile development', 'cloud', 'aws', 'azure', 'git', 'docker']
        for skill in tech_skills:
            if skill in cert_text:
                cv_skills.add(skill)
    
    # Extract skills from work experience
    if cv['work_experience']:
        exp_text = cv['work_experience'].lower()
        for skill in ['python', 'java', 'javascript', 'react', 'node', 'sql', 'html', 'css', 
                     'flask', 'django', 'machine learning', 'data science', 'web development',
                     'mobile development', 'cloud', 'aws', 'azure', 'git', 'docker']:
            if skill in exp_text:
                cv_skills.add(skill)
    
    # Extract skills from projects
    if cv['projects']:
        proj_text = cv['projects'].lower()
        for skill in ['python', 'java', 'javascript', 'react', 'node', 'sql', 'html', 'css', 
                     'flask', 'django', 'machine learning', 'data science', 'web development',
                     'mobile development', 'cloud', 'aws', 'azure', 'git', 'docker']:
            if skill in proj_text:
                cv_skills.add(skill)
    
    # Get all internships
    cursor.execute("SELECT * FROM internships")
    internships = cursor.fetchall()
    
    # Calculate similarity for each internship
    recommendations = []
    for internship in internships:
        required_skills = set(skill.strip().lower() for skill in internship['required_skills'].split(',')) if internship['required_skills'] else set()
        
        if not required_skills:
            continue
        
        # Calculate multiple similarity scores
        skill_similarity = 0
        if cv_skills:
            intersection = len(cv_skills & required_skills)
            union = len(cv_skills | required_skills)
            skill_similarity = intersection / union if union > 0 else 0
        
        # Education level matching (basic implementation)
        education_bonus = 0
        if cv['education'] and internship['description']:
            edu_text = cv['education'].lower()
            desc_text = internship['description'].lower()
            if any(degree in edu_text for degree in ['bachelor', 'master', 'phd', 'degree']):
                education_bonus = 0.1
        
        # Experience matching
        experience_bonus = 0
        if cv['work_experience'] and internship['description']:
            exp_text = cv['work_experience'].lower()
            desc_text = internship['description'].lower()
            # Simple keyword matching for experience relevance
            if any(keyword in exp_text for keyword in ['intern', 'developer', 'programmer', 'analyst']):
                experience_bonus = 0.1
        
        # Combined similarity score
        total_similarity = skill_similarity + education_bonus + experience_bonus
        
        if total_similarity > 0.15:  # Lower threshold for CV-based recommendations
            # Get company information
            cursor.execute("SELECT name FROM users WHERE id=?", (internship['company_id'],))
            company = cursor.fetchone()
            company_name = company['name'] if company else 'Unknown Company'
            
            recommendations.append({
                'id': internship['id'],
                'title': internship['title'],
                'description': internship['description'],
                'required_skills': internship['required_skills'],
                'posted_at': internship['posted_at'],
                'company_name': company_name,
                'company_id': internship['company_id'],
                'similarity': total_similarity,
                'type': 'CV-based',
                'skill_match': skill_similarity,
                'education_bonus': education_bonus,
                'experience_bonus': experience_bonus
            })
    
    # Sort by similarity
    recommendations.sort(key=lambda x: x['similarity'], reverse=True)
    return recommendations[:5]  # Top 5

def collaborative_filtering(user_id, cursor):
    """Collaborative filtering recommendation algorithm."""
    # Get applications of similar students
    # Step 1: Find students with similar applications
    cursor.execute("SELECT student_id, internship_id FROM applications")
    all_applications = cursor.fetchall()
    
    # Build user-item matrix
    user_items = {}
    for app in all_applications:
        student_id = app['student_id']
        internship_id = app['internship_id']
        if student_id not in user_items:
            user_items[student_id] = set()
        user_items[student_id].add(internship_id)
    
    # Find similar students based on Jaccard similarity
    current_user_apps = user_items.get(user_id, set())
    similar_students = []
    
    for student_id, apps in user_items.items():
        if student_id == user_id:
            continue
            
        intersection = len(current_user_apps & apps)
        union = len(current_user_apps | apps)
        similarity = intersection / union if union > 0 else 0
        
        if similarity > 0:
            similar_students.append((student_id, similarity))
    
    # Sort by similarity
    similar_students.sort(key=lambda x: x[1], reverse=True)
    
    # Get top internships from similar students
    recommendations = []
    seen_internships = set(current_user_apps)  # Exclude internships already applied to
    
    for student_id, similarity in similar_students[:3]:  # Top 3 similar students
        for internship_id in user_items[student_id]:
            if internship_id not in seen_internships:
                cursor.execute("SELECT * FROM internships WHERE id=?", (internship_id,))
                internship = cursor.fetchone()
                if internship:
                    # Get company information
                    cursor.execute("SELECT name FROM users WHERE id=?", (internship['company_id'],))
                    company = cursor.fetchone()
                    company_name = company['name'] if company else 'Unknown Company'
                    
                    recommendations.append({
                        'id': internship['id'],
                        'title': internship['title'],
                        'description': internship['description'],
                        'required_skills': internship['required_skills'],
                        'posted_at': internship['posted_at'],
                        'company_name': company_name,
                        'company_id': internship['company_id'],
                        'similarity': similarity,
                        'type': 'Collaborative'
                    })
                    seen_internships.add(internship_id)
    
    return recommendations[:5]  # Top 5
