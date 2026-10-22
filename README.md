## 🎥 Issue Selection & Code Submission Tutorial

This video shows you how to tell us which issue you want to work on and how to submit your code.

[Watch the Tutorial] https://mailaub-my.sharepoint.com/:v:/g/personal/lmm46_mail_aub_edu/IQAPqEYQrN03SrCzrh4cOoMxARMXaHU4ki2RmEPUwwLex0k?e=lXrjRw
# AUB Collab
### Have an idea. Find your people. Build it together.

**AUB Collab** is an AUB-specific student collaboration platform designed to help students turn their ideas into real projects by connecting them with other students who have the skills, interests, and motivation to contribute.

Many AUB students have ideas for software projects, research initiatives, startups, social-impact initiatives, creative projects, and other activities they would like to pursue. However, turning an idea into reality often requires a team with different skills and backgrounds. At the same time, many students are actively looking for opportunities to gain practical experience, work on meaningful projects, develop their skills, and collaborate with other students.

AUB Collab aims to connect these two groups.

## Repository Structure

| Folder | Description |
| --- | --- |
| [`Frontend/`](./Frontend) | React + Vite web application |
| [`Backend/`](./Backend) | Django + Django REST Framework API |

> **Status:** the project has just been initialized. Both apps are bare scaffolds, and the features below describe what we are building.

## Getting Started

You need [Node.js](https://nodejs.org) 20+ and Python 3.11+.

```bash
# Backend (http://localhost:8000)
cd Backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py runserver

# Frontend (http://localhost:5173)
cd Frontend
npm install
npm run dev
```

See the README in each folder for more details.

## How It Works

A student with an idea can create a project on AUB Collab and provide information such as:

* Project title and description
* Problem or opportunity being addressed
* Project goals and expected outcome
* Project category
* Expected duration
* Estimated time commitment
* Required majors
* Required and preferred skills
* Number of collaborators needed
* Application deadline
* Project difficulty
* Additional information or requirements

Other students can then discover projects based on their interests, major, skills, availability, and preferred type of collaboration.

Students interested in a project can submit an application containing information such as:

* CV
* Major and year
* Relevant skills
* Previous projects or experience
* GitHub, portfolio, or LinkedIn
* Motivation for joining the project
* Availability and expected commitment

The project creator can review applications and select the collaborators they believe are the best fit.

## From Ideas to Teams

AUB Collab is designed around the complete transition from an idea to a team.

**Idea → Project → Applications → Team → Collaboration → Completed Project**

Once a team has been formed, the project can eventually have its own workspace where members can manage tasks, milestones, discussions, resources, and progress.

For example, a student might propose:

> **AI-Powered Campus Navigation**

The project could be looking for:

* 1 CCE student with backend experience
* 1 student with machine learning experience
* 1 UI/UX designer
* 1 business student to help with user research

Instead of the project remaining an idea, AUB Collab helps the student find the people necessary to build it.

## Projects Across Disciplines

AUB Collab is not limited to software development.

Students could create projects in areas such as:

* 💻 Technology and software
* 🔬 Research
* 🚀 Entrepreneurship and startups
* 🌍 Social impact
* 🎨 Design and creative work
* 🧪 Science and engineering
* 📚 Education
* 🎬 Media and content
* 🤝 Interdisciplinary initiatives

This allows students from different faculties and majors to collaborate on projects that require a combination of skills.

A CCE student could find a designer. A biology student could find a data scientist. A business student could find an engineer. A filmmaker could find a developer.

The platform is built around the idea that **great projects often require people with different backgrounds to work together.**

## Project Discovery and Matching

As the platform grows, AUB Collab can provide personalized project recommendations based on a student's:

* Major
* Skills
* Interests
* Previous projects
* Courses
* Availability
* Preferred project duration
* Experience level

Students could eventually see recommendations such as:

> **92% Match — AI-Powered Study Assistant**
>
> This project is looking for students with Python and frontend development experience. It requires approximately 5–8 hours per week for three months.

This creates opportunities for students who may not know where to find projects that match their interests.

## Student Profiles and Portfolios

AUB Collab can eventually allow students to build profiles based on their actual contributions.

Instead of simply listing skills, students can demonstrate them through projects they have participated in.

For example:

**Remy Hirwa**
Computer and Communication Engineering

**Skills:** Python · React · Backend · AI

**Projects**

* AI Study Assistant — Backend Developer
* Campus Navigation — Project Lead
* AUB Collab — Core Contributor

This gives students a way to demonstrate practical experience and collaboration beyond their academic coursework.

## A Platform That Students Build Together

AUB Collab is itself intended to be an open-source project.

Students can contribute to the development of the platform through the project's GitHub repository.

Issues will be organized by difficulty so that students with different levels of experience can participate.

### Easy

* Frontend improvements
* UI components
* Documentation
* Testing
* Accessibility improvements
* Bug fixes
* Form validation

### Medium

* API endpoints
* Database models
* Authentication features
* Search and filtering
* Notifications
* Application management
* Profile functionality

### Hard

* Project recommendation systems
* Student-project matching algorithms
* Search infrastructure
* Real-time collaboration
* Advanced authorization
* Performance optimization
* Distributed background processing
* Analytics infrastructure

This allows beginners to make their first contribution while giving experienced developers challenging engineering problems to solve.

## Long-Term Vision

The long-term goal of AUB Collab is to become an infrastructure layer for **student-led collaboration at AUB**.

A student should be able to come to the platform with nothing more than an idea and eventually leave with:

**An idea → a team → a project → real experience → something they can show the world.**

AUB Collab is therefore not simply a project board or a social network. It is a system designed to help students **find each other, build together, learn from one another, and turn ideas into tangible results.**

---

### AUB Collab

**Have an idea. Find your people. Build it together.**
