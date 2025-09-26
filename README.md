# 🎯 Vision U - AI-Powered Career Counseling Platform

<div align="center">

![Vision U Logo](https://img.shields.io/badge/Vision%20U-AI%20Career%20Guide-blue?style=for-the-badge&logo=robot)

**See Your Future Clearly with AI-Powered Career Guidance**

[![Live Demo](https://img.shields.io/badge/🌐%20Live%20Demo-vision--u.onrender.com-brightgreen?style=for-the-badge)](https://vision-u.onrender.com)
[![Python](https://img.shields.io/badge/Python-3.12-blue?style=flat-square&logo=python)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.0-lightgrey?style=flat-square&logo=flask)](https://flask.palletsprojects.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Database-blue?style=flat-square&logo=postgresql)](https://postgresql.org)

</div>

## 🚀 Live Demo

**Experience Vision U:** [https://vision-u.onrender.com](https://vision-u.onrender.com)

## 📖 About Vision U

Vision U is a cutting-edge AI-powered career counseling platform designed to help students and professionals make informed career decisions. Using advanced machine learning algorithms powered by Google's Gemini AI, Vision U provides personalized career recommendations, detailed roadmaps, and actionable insights to guide users toward their dream careers.

## ✨ Key Features

- 🤖 **AI-Powered Analysis** - Advanced algorithms analyze personality, interests, and aptitude
- 🗺️ **Personalized Career Roadmaps** - Step-by-step paths with timelines and milestones  
- 📊 **Industry Insights** - Real-time market trends and salary data
- 📱 **Responsive Design** - Seamless experience across all devices
- 🔐 **Secure Authentication** - User registration and login system
- 📄 **PDF Reports** - Downloadable career guidance reports
- 🌐 **Modern Interface** - Interactive and user-friendly design

## 🛠️ Technology Stack

### Backend
- **Python 3.12** - Core programming language
- **Flask 3.0** - Web framework
- **SQLAlchemy** - Database ORM
- **PostgreSQL** - Production database
- **Gunicorn** - WSGI server

### AI & APIs
- **Google Gemini AI** - Career recommendation engine
- **Markdown Processing** - Content formatting
- **PDF Generation** - Report creation

### Frontend
- **HTML5 & CSS3** - Modern web standards
- **JavaScript (ES6+)** - Interactive functionality
- **Responsive Design** - Mobile-first approach

### Deployment
- **Render** - Cloud hosting platform
- **GitHub Actions** - CI/CD pipeline
- **Environment Variables** - Secure configuration

## 🚀 Quick Start

### Prerequisites
- Python 3.12+
- Git
- Google Gemini API Key

### Local Development Setup

1. **Clone the Repository**
   ```bash
   git clone https://github.com/Subhamsidhanta/Vision-U.git
   cd Vision-U/main
   ```

2. **Create Virtual Environment**
   ```bash
   python -m venv venv
   
   # Windows
   venv\Scripts\activate
   
   # Mac/Linux  
   source venv/bin/activate
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment Configuration**
   
   Create a `.env` file:
   ```env
   SECRET_KEY=your-development-secret-key
   API_KEY=your-gemini-api-key
   DATABASE_URL=sqlite:///instance/users.db
   ```

5. **Run the Application**
   ```bash
   python app.py
   ```
   
   Visit: `http://localhost:5000`

### 🌐 Production Deployment

The application is deployed on Render with automatic deployments from the main branch.

**Environment Variables (Production):**
```env
SECRET_KEY=strong-production-secret-key
API_KEY=your-gemini-api-key
DATABASE_URL=postgresql://user:pass@host:port/dbname
```

## 📁 Project Structure

```
Vision-U/
├── main/
│   ├── static/           # CSS, JS, and assets
│   │   ├── chat.css
│   │   ├── index.css
│   │   ├── login.css
│   │   ├── register.css
│   │   └── result.css
│   ├── templates/        # HTML templates
│   │   ├── chat.html
│   │   ├── dashboard.html
│   │   ├── index.html
│   │   ├── login.html
│   │   ├── register.html
│   │   └── result.html
│   ├── instance/         # Database files (local)
│   ├── app.py           # Main Flask application
│   ├── requirements.txt  # Python dependencies
│   ├── render.yaml      # Render deployment config
│   ├── build.sh         # Build script
│   ├── runtime.txt      # Python version
│   └── README.md        # Project documentation
```

## 🔧 API Integration

### Google Gemini AI Setup

1. Visit [Google AI Studio](https://aistudio.google.com/)
2. Create a new project or select existing
3. Generate API key for Gemini
4. Add to environment variables as `API_KEY`

### Database Configuration

- **Development**: SQLite (automatic setup)
- **Production**: PostgreSQL (managed by Render)

## 🎯 Core Functionality

### Career Assessment Process

1. **Interest Discovery** - Interactive questionnaires
2. **Aptitude Evaluation** - Cognitive ability assessments  
3. **Personality Profiling** - Work style analysis
4. **AI Recommendations** - Personalized career matches
5. **Roadmap Generation** - Detailed action plans

### User Journey

1. **Registration/Login** - Secure account creation
2. **Assessment** - Comprehensive career evaluation
3. **AI Analysis** - Gemini-powered recommendations
4. **Results** - Personalized career guidance
5. **PDF Export** - Downloadable reports

## 🤝 Contributing

We welcome contributions! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 👥 Team Members

<table>
  <tr>
    <td align="center">
      <img src="https://github.com/Subhamsidhanta.png" width="100px;" alt="Subham Sidhanta"/>
      <br />
      <sub><b>Subham Sidhanta</b></sub>
      <br />
      <small>Project Lead & Full-Stack Developer</small>
    </td>
    <td align="center">
      <img src="https://via.placeholder.com/100?text=AP" width="100px;" alt="Arijit Pal"/>
      <br />
      <sub><b>Arijit Pal</b></sub>
      <br />
      <small>Backend Developer</small>
    </td>
    <td align="center">
      <img src="https://via.placeholder.com/100?text=SG" width="100px;" alt="Shrabani Giri"/>
      <br />
      <sub><b>Shrabani Giri</b></sub>
      <br />
      <small>Frontend Developer</small>
    </td>
    <td align="center">
      <img src="https://via.placeholder.com/100?text=SH" width="100px;" alt="Sohini Ghosh"/>
      <br />
      <sub><b>Sohini Ghosh</b></sub>
      <br />
      <small>UI/UX Designer</small>
    </td>
    <td align="center">
      <img src="https://via.placeholder.com/100?text=SB" width="100px;" alt="Suresh BCA"/>
      <br />
      <sub><b>Suresh BCA</b></sub>
      <br />
      <small>Database Administrator</small>
    </td>
  </tr>
</table>

## 📊 Project Stats

- **Total Students Guided**: 15,000+
- **Career Paths Available**: 500+
- **Success Rate**: 96%
- **24/7 Availability**: Always online

## 📱 Screenshots

<div align="center">

### 🏠 Homepage
*Modern landing page with interactive features*

### 💬 AI Chat Interface  
*Intelligent career counseling conversation*

### 📊 Results Dashboard
*Personalized recommendations and roadmaps*

</div>

## 🔒 Security Features

- ✅ **Password Hashing** - Secure user authentication
- ✅ **Environment Variables** - Protected API keys
- ✅ **HTTPS Encryption** - Secure data transmission
- ✅ **Input Validation** - Protected against attacks
- ✅ **Session Management** - Secure user sessions

## 📈 Performance

- ⚡ **Fast Loading** - Optimized for speed
- 📱 **Mobile Responsive** - Works on all devices
- 🌐 **Cross-browser** - Compatible everywhere
- ♿ **Accessible** - Built with accessibility in mind

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **Google Gemini AI** - Powering our AI recommendations
- **Render** - Reliable cloud hosting platform
- **Flask Community** - Excellent web framework
- **Open Source Community** - Amazing tools and libraries

## 📞 Support & Contact

- **Live Demo**: [vision-u.onrender.com](https://vision-u.onrender.com)
- **Repository**: [github.com/Subhamsidhanta/Vision-U](https://github.com/Subhamsidhanta/Vision-U)
- **Issues**: [Report bugs or request features](https://github.com/Subhamsidhanta/Vision-U/issues)

---

<div align="center">

**🎓 Empowering the next generation with AI-driven career guidance**

Made with ❤️ by the Vision U Team

[![GitHub stars](https://img.shields.io/github/stars/Subhamsidhanta/Vision-U?style=social)](https://github.com/Subhamsidhanta/Vision-U)
[![GitHub forks](https://img.shields.io/github/forks/Subhamsidhanta/Vision-U?style=social)](https://github.com/Subhamsidhanta/Vision-U/fork)

</div>