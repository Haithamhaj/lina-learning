#!/usr/bin/env python3
"""Internal operator CLI. DB credentials confer access; never expose as a public endpoint."""
import argparse
import json
from uuid import UUID
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from services.canvas_review.service import capture_review, analyze_review, get_review, list_experiences, list_reviews
from services.model_gateway.factory import create_canvas_development_review_gateway
from services.platform.config import Settings
from services.platform.db.connection import normalize_database_url
from services.platform.storage import create_object_storage


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['list', 'reviews', 'capture', 'analyze', 'show', 'evidence'])
    parser.add_argument('--student-id', required=True, type=UUID)
    parser.add_argument('--run-id', type=UUID)
    parser.add_argument('--review-id', type=UUID)
    parser.add_argument('--requested-by')
    parser.add_argument('--env-file')
    parser.add_argument('--live', action='store_true', help='Authorize the on-demand provider call')
    parser.add_argument('--no-preview', action='store_true')
    parser.add_argument('--offset', type=int, default=0)
    args = parser.parse_args()
    settings = Settings(_env_file=args.env_file) if args.env_file else Settings()
    engine = create_engine(normalize_database_url(settings.database_url))
    factory = sessionmaker(engine, expire_on_commit=False)
    try:
        if args.command == 'list':
            with factory() as session:
                result = list_experiences(session, student_id=args.student_id, offset=args.offset)
        elif args.command == 'reviews':
            with factory() as session:
                result = list_reviews(session, student_id=args.student_id, run_id=args.run_id, offset=args.offset)
        elif args.command == 'capture':
            if not args.run_id or not args.requested_by:
                parser.error('capture requires --run-id and --requested-by')
            identity = capture_review(factory, storage=create_object_storage(settings), student_id=args.student_id,
                run_id=args.run_id, requested_by=args.requested_by, preview=not args.no_preview)
            result = {'review_id': str(identity), 'status': 'READY'}
        else:
            if not args.review_id:
                parser.error('command requires --review-id')
            if args.command == 'analyze':
                if not args.live:
                    parser.error('analyze requires --live for an explicit provider request')
                result = analyze_review(factory, student_id=args.student_id, review_id=args.review_id,
                    gateway_factory=lambda session: create_canvas_development_review_gateway(session, settings=settings),
                    storage=create_object_storage(settings))
            else:
                with factory() as session:
                    row = get_review(session, student_id=args.student_id, review_id=args.review_id)
                    result = row.evidence_manifest if args.command == 'evidence' else {'review_id': str(row.id), 'status': row.status, 'report': row.report,
                        'failure_code': row.failure_code, 'evidence_sha256': row.evidence_manifest.get('sha256')}
        print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    finally:
        engine.dispose()


if __name__ == '__main__':
    main()
