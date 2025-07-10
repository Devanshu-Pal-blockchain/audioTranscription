# VTO Meeting Transcription System

## Overview

This is a comprehensive VTO (Vision, Traction, Organizer) system that has been upgraded from an EOS-centric meeting transcription platform to support the full spectrum of VTO methodologies including yearly, quarterly, and weekly meetings with advanced IDS (Issues, Decisions, Solutions) workflow management.

## System Architecture

### Core Components

1. **Meeting Management**
   - Yearly, Quarterly, and Weekly meeting types
   - Advanced transcript analysis and time slot tracking
   - Attendee management and access controls

2. **IDS Workflow**
   - Issue identification and categorization
   - Decision tracking and implementation
   - Solution development and monitoring
   - Cross-meeting continuity

3. **Rock Management**
   - Annual, Company, and Individual rocks
   - Progress tracking with milestones
   - Success metrics and completion monitoring

4. **Analytics & Dashboards**
   - VTO health metrics and KPIs
   - Trend analysis and predictive insights
   - Individual and team performance tracking

5. **Enhanced RAG System**
   - AI-powered transcript analysis
   - Semantic search across all content
   - Context-aware insights and recommendations

## New Features in VTO 2.0

### Enhanced Models
- **Meeting**: Complete meeting lifecycle management
- **Issue**: Structured issue tracking with categories and priorities
- **Solution**: Solution development and implementation tracking
- **Milestone**: Detailed milestone management with progress tracking
- **TimeSlot**: Granular time-based analysis of meeting content

### Advanced Analytics
- VTO health scoring
- Rock completion forecasting
- Issue resolution trends
- Meeting effectiveness metrics
- Cross-functional collaboration analysis

### AI-Powered Features
- Automatic IDS extraction from transcripts
- Semantic search and content discovery
- Predictive analytics for goal achievement
- Intelligent insights and recommendations

## API Endpoints

### Authentication
- `POST /auth/login` - User authentication
- `POST /auth/register-admin` - Admin registration

### Meetings
- `POST /api/meetings` - Create meeting
- `GET /api/meetings` - List meetings with filters
- `GET /api/meetings/{id}` - Get meeting details
- `GET /api/meetings/{id}/summary` - Get meeting summary with IDS analysis
- `POST /api/meetings/{id}/process-transcript` - Process transcript for IDS extraction

### Issues, Decisions, Solutions (IDS)
- `POST /api/issues` - Create issue
- `GET /api/issues` - List issues with filters
- `PUT /api/issues/{id}` - Update issue
- `POST /api/solutions` - Create solution
- `GET /api/solutions` - List solutions
- `GET /api/issues/{id}/solutions` - Get solutions for specific issue

### Milestones
- `POST /api/milestones` - Create milestone
- `GET /api/milestones` - List milestones
- `POST /api/milestones/{id}/update-progress` - Update milestone progress
- `GET /api/milestones/upcoming` - Get upcoming milestones
- `GET /api/milestones/overdue` - Get overdue milestones

### Time Slots
- `POST /api/time-slots` - Create time slot
- `GET /api/time-slots` - List time slots
- `GET /api/meetings/{id}/time-slots` - Get meeting time slots
- `GET /api/analytics/speaking-time` - Speaking time analytics

### Analytics & Dashboards
- `GET /api/analytics/dashboard/overview` - Comprehensive dashboard
- `GET /api/analytics/dashboard/vto-health` - VTO health metrics
- `GET /api/analytics/dashboard/rock-progress` - Rock progress dashboard
- `GET /api/analytics/dashboard/ids-analytics` - IDS analytics
- `GET /api/analytics/reports/quarterly-review` - Quarterly report

### Enhanced RAG
- `POST /api/rag/rag/query` - Query RAG system
- `POST /api/rag/rag/semantic-search` - Semantic search
- `POST /api/rag/rag/generate-insights` - AI-powered insights
- `GET /api/rag/rag/trending-topics` - Trending topics analysis

### Enhanced Rocks
- `GET /rocks/type/{type}` - List rocks by type (annual/company/individual)
- `POST /rocks/{id}/update-progress` - Update rock progress
- `GET /rocks/analytics/completion-rate` - Completion analytics
- `GET /rocks/analytics/at-risk` - At-risk rocks

## Installation & Setup

### Prerequisites
- Python 3.8+
- MongoDB
- Qdrant Vector Database
- Redis (for caching)

### Installation Steps

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd audioTranscription/Backend
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Environment Setup**
   Create a `.env` file with:
   ```env
   MONGODB_URL=mongodb://localhost:27017/vto_db
   QDRANT_URL=http://localhost:6333
   SECRET_KEY=your-secret-key
   ALGORITHM=HS256
   ```

4. **Run Database Migration**
   ```bash
   python vto_migration.py
   ```

5. **Start the API Server**
   ```bash
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

## Database Migration

The system includes a comprehensive migration script (`vto_migration.py`) that:
- Creates new collections for VTO entities
- Adds indexes for optimal performance
- Migrates existing data to new VTO structure
- Sets up RAG embeddings collections
- Creates sample configuration data

Run migration:
```bash
python vto_migration.py
```

Or via API (admin only):
```bash
POST /admin/migration/run-vto-migration
```

## Testing

### Comprehensive Test Suite
Run the complete test suite:
```bash
python test_vto_api.py
```

### Performance Testing
```bash
python test_vto_api.py performance
```

### Generate Test Data
```bash
python test_vto_api.py generate-data
```

## Configuration

### Meeting Types Configuration
The system supports configurable meeting types with templates:
- **Yearly**: Annual vision and planning (8 hours)
- **Quarterly**: Quarterly rock setting and review (4 hours)
- **Weekly**: Weekly Level 10 meetings (90 minutes)

### VTO Permissions
Users have granular permissions:
- `can_create_meetings`
- `can_manage_rocks`
- `can_view_analytics`
- `can_access_all_quarters`

## Development

### Adding New Endpoints
1. Create new route in `routes/` directory
2. Add to main.py imports and router includes
3. Update test suite in `test_vto_api.py`

### Extending Models
1. Add fields to Pydantic models in `models/`
2. Update corresponding service in `service/`
3. Add database migration logic
4. Update API endpoints as needed

### RAG Enhancement
The RAG system supports:
- Automatic content indexing
- Semantic search with embeddings
- Context-aware query processing
- Cross-content relationship analysis

## Monitoring & Health

### Health Check Endpoints
- `GET /admin/system/health` - Basic system health
- `GET /api/rag/rag/health-check` - RAG system health
- `GET /admin/migration/validate-vto` - Migration validation

### Performance Monitoring
- Response times tracked per endpoint
- Concurrent request handling
- Database query optimization
- Vector search performance

## Security

### Authentication & Authorization
- JWT-based authentication
- Role-based access control (admin/user)
- Per-resource permission checking
- User data isolation for non-admins

### Data Privacy
- User-specific data filtering
- Meeting attendee access controls
- Secure transcript handling
- Audit logging for sensitive operations

## Troubleshooting

### Common Issues

1. **Migration Fails**
   - Check MongoDB connection
   - Verify user permissions
   - Review migration logs

2. **RAG Queries Return Empty**
   - Ensure content is indexed
   - Check Qdrant connection
   - Verify embedding model availability

3. **Authentication Errors**
   - Verify JWT secret configuration
   - Check token expiration
   - Validate user credentials

### Debug Mode
Start server with debug logging:
```bash
uvicorn main:app --reload --log-level debug
```

## Future Enhancements

### Planned Features
- Real-time collaboration
- Mobile app support
- Advanced AI insights
- Integration with external tools
- Voice-to-text improvements
- Custom dashboard widgets

### Extensibility
The system is designed for easy extension:
- Plugin architecture for new meeting types
- Configurable workflow templates
- Custom analytics modules
- Third-party integrations

## Contributing

1. Fork the repository
2. Create feature branch
3. Add comprehensive tests
4. Update documentation
5. Submit pull request

## License

[License information]

## Support

For support and questions:
- Check documentation
- Review test examples
- Submit issues via GitHub
- Contact development team

---

*VTO Meeting Transcription System v2.0 - Comprehensive Vision, Traction, and Organization Management*
