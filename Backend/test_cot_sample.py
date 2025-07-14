#!/usr/bin/env python3
"""
Chain of Thought Pipeline Test with Sample Data
Tests the CoT implementation with realistic meeting scenarios
"""

import asyncio
import json
from datetime import datetime
from service.script_pipeline_service import PipelineService

async def test_with_sample_data():
    """Test CoT pipeline with realistic meeting transcript"""
    print('🔥 Testing CoT Pipeline with Sample Meeting Data')
    print('=' * 60)
    
    # Sample meeting transcript with clear assignments and tasks
    sample_transcript = {
        'full_transcript': '''
        Sarah Johnson opened the meeting by discussing our Q4 strategic objectives. She emphasized the need to improve our customer satisfaction scores from 7.2 to 8.5 by the end of the quarter. Michael Chen volunteered to lead the user experience improvement initiative and committed to delivering wireframes by next Friday.
        
        Emily Davis raised concerns about our current security infrastructure. She mentioned that we've had three minor security incidents this month and recommended implementing multi-factor authentication across all systems. David Thompson agreed to conduct a comprehensive security audit within the next two weeks.
        
        Robert Williams presented the financial performance metrics. He noted that our revenue growth has slowed to 12% this quarter, down from 18% last quarter. He suggested we need to diversify our product offerings and proposed launching a new feature set by December 15th.
        
        Amanda Rodriguez discussed the marketing campaign performance. She reported that our conversion rates have improved by 23% since implementing the new email automation system. She wants to expand this to social media channels and needs approval for a $50,000 marketing budget increase.
        
        Christopher Lee brought up technical debt issues. He explained that our system response times have degraded by 40% over the past month due to legacy code. He proposed a systematic refactoring project that would take approximately 8 weeks to complete and require 3 additional developers.
        
        Jennifer Martinez discussed HR initiatives. She mentioned that employee satisfaction scores have dropped to 6.8 and proposed implementing a flexible work arrangement policy. She committed to drafting a policy proposal by the end of this week and conducting employee feedback sessions.
        
        The team also discussed the upcoming SOC 2 compliance audit. Sarah Johnson assigned Emily Davis to coordinate with the external auditors and ensure all documentation is ready by November 1st. Michael Chen raised concerns about the mobile app performance issues affecting user onboarding.
        
        David Thompson reported that the new backup system implementation is 75% complete and should be finished by next Tuesday. Amanda Rodriguez requested additional marketing analytics tools to better track campaign ROI and customer acquisition costs.
        
        Christopher Lee mentioned that the API rate limiting feature needs to be implemented before the next major release. He assigned this task to his senior developer team and set a deadline of October 30th.
        
        Jennifer Martinez brought up the need for diversity and inclusion training for all management staff. She proposed a quarterly training program starting in Q1 2026 and requested budget approval for external facilitators.
        '''
    }
    
    # Sample participants (matching names in transcript)
    participants = [
        {'employee_name': 'Sarah Johnson', 'employee_designation': 'CEO', 'employee_responsibilities': 'Strategic leadership, customer satisfaction'},
        {'employee_name': 'Michael Chen', 'employee_designation': 'Head of Product', 'employee_responsibilities': 'Product development, user experience'},
        {'employee_name': 'Emily Davis', 'employee_designation': 'IT Security Manager', 'employee_responsibilities': 'Information security, compliance'},
        {'employee_name': 'David Thompson', 'employee_designation': 'IT Director', 'employee_responsibilities': 'IT infrastructure, security audits'},
        {'employee_name': 'Robert Williams', 'employee_designation': 'CFO', 'employee_responsibilities': 'Financial planning, revenue analysis'},
        {'employee_name': 'Amanda Rodriguez', 'employee_designation': 'Marketing Director', 'employee_responsibilities': 'Marketing campaigns, customer acquisition'},
        {'employee_name': 'Christopher Lee', 'employee_designation': 'CTO', 'employee_responsibilities': 'Technology strategy, system architecture'},
        {'employee_name': 'Jennifer Martinez', 'employee_designation': 'HR Director', 'employee_responsibilities': 'Human resources, employee engagement'}
    ]
    
    pipeline = PipelineService()
    
    try:
        print('📊 Running semantic tokenization...')
        semantic_data = pipeline.semantic_tokenization(sample_transcript)
        segments_count = len(semantic_data["semantic_tokens"])
        print(f'✅ Created {segments_count} segments')
        
        print('🧠 Running CoT segment analysis...')
        segment_analyses = await pipeline.parallel_segment_analysis(semantic_data)
        print(f'✅ Analyzed {len(segment_analyses)} segments with CoT reasoning')
        
        # Check for CoT reasoning indicators
        total_analysis_length = sum(len(analysis.get('analysis', '')) for analysis in segment_analyses)
        cot_indicators = [
            'STEP 1:', 'STEP 2:', 'STEP 3:', 'STEP 4:', 'STEP 5:', 
            'CONTEXT ANALYSIS', 'TASK EXTRACTION', 'ASSIGNMENT VALIDATION',
            'SPEAKER AND CONTEXT', 'TASK AND RESPONSIBILITY', 'BUSINESS CONTEXT'
        ]
        
        cot_found = 0
        detailed_analysis = []
        
        for i, analysis in enumerate(segment_analyses):
            analysis_text = analysis.get('analysis', '')
            has_cot = any(indicator in analysis_text for indicator in cot_indicators)
            if has_cot:
                cot_found += 1
            
            detailed_analysis.append({
                'segment_id': i,
                'length': len(analysis_text),
                'has_cot': has_cot,
                'people_mentioned': len(analysis.get('people', [])),
                'action_items': len(analysis.get('action_items', []))
            })
        
        print(f'📈 Total analysis content: {total_analysis_length} characters')
        print(f'🧠 Segments with CoT reasoning: {cot_found}/{len(segment_analyses)}')
        
        # Show detailed segment analysis
        print('\n📋 Detailed Segment Analysis:')
        for detail in detailed_analysis:
            cot_status = "✅ CoT" if detail['has_cot'] else "❌ No CoT"
            print(f'  Segment {detail["segment_id"]}: {detail["length"]} chars, {detail["people_mentioned"]} people, {detail["action_items"]} actions - {cot_status}')
        
        print('\n🎯 Generating ROCKS with CoT...')
        rocks_data = await pipeline.generate_rocks(segment_analyses, 12, participants)
        
        if 'error' not in rocks_data:
            print('✅ ROCKS generation successful!')
            
            # Analyze the results
            rocks = rocks_data.get('rocks', [])
            todos = rocks_data.get('todos', [])
            issues = rocks_data.get('issues', [])
            runtime_solutions = rocks_data.get('runtime_solutions', [])
            
            print(f'📊 Generated: {len(rocks)} rocks, {len(todos)} todos, {len(issues)} issues, {len(runtime_solutions)} runtime solutions')
            
            # Check assignments in detail
            assigned_rocks = [r for r in rocks if r.get('rock_owner', 'UNASSIGNED') != 'UNASSIGNED' and not r.get('rock_owner', '').startswith('UNASSIGNED')]
            assigned_todos = [t for t in todos if t.get('assigned_to', 'UNASSIGNED') != 'UNASSIGNED' and not t.get('assigned_to', '').startswith('UNASSIGNED')]
            assigned_issues = [i for i in issues if i.get('raised_by', 'UNASSIGNED') != 'UNASSIGNED' and not i.get('raised_by', '').startswith('UNASSIGNED')]
            
            print(f'✅ Properly assigned: {len(assigned_rocks)}/{len(rocks)} rocks, {len(assigned_todos)}/{len(todos)} todos, {len(assigned_issues)}/{len(issues)} issues')
            
            # Check milestones completeness
            complete_milestones = [r for r in rocks if len(r.get('milestones', [])) == 12]
            print(f'📅 ROCKS with complete 12-week milestones: {len(complete_milestones)}/{len(rocks)}')
            
            # Show assignment details
            print('\n👥 Assignment Analysis:')
            for i, rock in enumerate(rocks):
                owner = rock.get('rock_owner', 'UNASSIGNED')
                milestone_count = len(rock.get('milestones', []))
                status = "✅ Assigned" if owner != 'UNASSIGNED' and not owner.startswith('UNASSIGNED') else "⚠️ Unassigned"
                milestone_status = f"📅 {milestone_count}/12 weeks"
                print(f'  Rock {i+1}: {rock.get("smart_rock", "Unknown")[:50]}... -> {owner} ({status}) {milestone_status}')
            
            # Check for "UNASSIGNED" issues that were fixed by CoT
            unassigned_count = sum(1 for item in rocks + todos + issues if 
                                 item.get('rock_owner', item.get('assigned_to', item.get('raised_by', ''))).startswith('UNASSIGNED'))
            
            print(f'\n🎯 CoT Assignment Success Rate:')
            total_items = len(rocks) + len(todos) + len(issues)
            assigned_items = total_items - unassigned_count
            success_rate = (assigned_items / total_items * 100) if total_items > 0 else 0
            print(f'  Total items: {total_items}')
            print(f'  Properly assigned: {assigned_items}')
            print(f'  Success rate: {success_rate:.1f}%')
            
            # Save detailed results for analysis
            results_summary = {
                'test_timestamp': datetime.now().isoformat(),
                'segments_analyzed': len(segment_analyses),
                'cot_segments': cot_found,
                'total_analysis_length': total_analysis_length,
                'generated_items': {
                    'rocks': len(rocks),
                    'todos': len(todos),
                    'issues': len(issues),
                    'runtime_solutions': len(runtime_solutions)
                },
                'assignment_success': {
                    'assigned_rocks': len(assigned_rocks),
                    'assigned_todos': len(assigned_todos),
                    'assigned_issues': len(assigned_issues),
                    'success_rate': success_rate
                },
                'milestone_completeness': {
                    'complete_milestones': len(complete_milestones),
                    'total_rocks': len(rocks)
                },
                'detailed_segment_analysis': detailed_analysis
            }
            
            with open('cot_test_results.json', 'w', encoding='utf-8') as f:
                json.dump(results_summary, f, indent=2, ensure_ascii=False)
            
            print(f'\n📁 Detailed results saved to: cot_test_results.json')
            print('\n🎉 Sample test completed successfully!')
            
        else:
            error_msg = rocks_data.get('error', 'Unknown error')
            print(f'❌ ROCKS generation failed: {error_msg}')
            
            # Save error details
            error_summary = {
                'test_timestamp': datetime.now().isoformat(),
                'error': error_msg,
                'segments_analyzed': len(segment_analyses) if 'segment_analyses' in locals() else 0,
                'semantic_data_available': 'semantic_data' in locals()
            }
            
            with open('cot_test_error.json', 'w', encoding='utf-8') as f:
                json.dump(error_summary, f, indent=2, ensure_ascii=False)
            
            print(f'📁 Error details saved to: cot_test_error.json')
            
    except Exception as e:
        print(f'❌ Test failed: {e}')
        import traceback
        traceback.print_exc()
        
        # Save exception details
        exception_summary = {
            'test_timestamp': datetime.now().isoformat(),
            'exception': str(e),
            'traceback': traceback.format_exc()
        }
        
        with open('cot_test_exception.json', 'w', encoding='utf-8') as f:
            json.dump(exception_summary, f, indent=2, ensure_ascii=False)
        
        print(f'📁 Exception details saved to: cot_test_exception.json')

def main():
    """Main test runner"""
    print('🚀 Starting CoT Pipeline Sample Test')
    print('=' * 60)
    
    try:
        asyncio.run(test_with_sample_data())
    except KeyboardInterrupt:
        print('\n⚠️ Test interrupted by user')
    except Exception as e:
        print(f'\n❌ Test runner failed: {e}')
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
