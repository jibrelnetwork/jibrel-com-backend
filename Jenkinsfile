builder(
        jUnitReportsPath: 'junit-reports',
        coverageReportsPath: 'coverage-reports',
        slackTargetNames: '#radio-jibrelcom',
        slackNotificationBranchFilter: '^(master|develop|(release|feature|bugfix)/[a-zA-z0-9.-]*)$',
        buildTasks: [
                [
                        name: "Swagger",
                        type: "lint",
                        method: "inside",
                        runAsUser: "root",
                        entrypoint: "",
                        command: [
                                'pip install openapi-spec-validator',
                                'openapi-spec-validator v1.swagger.yml',
                        ]
                ],
                [
                        name: "Migrations",
                        type: "lint",
                        method: "inside",
                        runAsUser: "root",
                        entrypoint: "",
                        environment: [
                                DOMAIN_NAME: 'localhost',
                                DJANGO_ALLOWED_HOSTS: 'localhost',
                                MAIN_DB_HOST: 'jibrel',
                                MAIN_DB_PORT: 5432,
                                MAIN_DB_NAME: 'jibrel_db',
                                MAIN_DB_USER: 'postgres',
                                MAIN_DB_USER_PASSWORD: 'postgres',
                                DJANGO_SECRET_KEY: 'euy7ohngaighei2Eong8kaiYae2ooH2e',
                                REDIS_HOST: 'redis',
                        ],
                        sidecars: [
                                jibrel: [
                                        image: 'postgres:11-alpine',
                                        environment: [
                                              POSTGRES_USER: 'postgres',
                                              POSTGRES_PASSWORD: 'postgres',
                                              POSTGRES_DB: 'jibrel_db',
                                        ]
                                ],
                                redis: [
                                        image: 'redis:5.0-alpine',
                                ]
                        ],
                        command: [
                                'python manage.py makemigrations --dry-run --check',
                        ]
                ],
                [
                        name: "Linters",
                        type: "lint",
                        method: "inside",
                        runAsUser: "root",
                        entrypoint: "",
                        jUnitPath: '/junit-reports',
                        environment: [
                                DJANGO_SECRET_KEY: 'euy7ohngaighei2Eong8kaiYae2ooH2e',
                        ],
                        command: [
                                'pip install --no-cache-dir poetry==0.12.16',
                                'poetry install',
                                'mkdir -p /junit-reports',
                                'isort -vb -rc -m 3 -e -fgw -q -c',
                                'py.test --pylama --pylama-only --junit-xml /junit-reports/pylama-report.xml',
                                'mypy --junit-xml=/junit-reports/mypy-junit-report.xml jibrel',
                        ],
                ],
                [
                        name: 'Tests',
                        type: 'test',
                        method: 'inside',
                        runAsUser: 'root',
                        entrypoint: '',
                        jUnitPath: '/junit-reports',
                        coveragePath: '/coverage-reports',
                        environment: [
                                DOMAIN_NAME: 'localhost',
                                DJANGO_ALLOWED_HOSTS: 'localhost',
                                MAIN_DB_HOST: 'jibrel',
                                MAIN_DB_PORT: 5432,
                                MAIN_DB_NAME: 'jibrel_db',
                                MAIN_DB_USER: 'postgres',
                                MAIN_DB_USER_PASSWORD: 'postgres',
                                DJANGO_SECRET_KEY: 'euy7ohngaighei2Eong8kaiYae2ooH2e',
                                REDIS_HOST: 'redis',
                        ],
                        sidecars: [
                                jibrel: [
                                        image: 'postgres:11-alpine',
                                        environment: [
                                              POSTGRES_USER: 'postgres',
                                              POSTGRES_PASSWORD: 'postgres',
                                              POSTGRES_DB: 'jibrel_db',
                                        ]
                                ],
                                redis: [
                                        image: 'redis:5.0-alpine',
                                ]
                        ],
                        command: [
                                'pip install --no-cache-dir poetry==0.12.16',
                                'poetry install',
                                'mkdir -p /junit-reports',
                                'pytest --junitxml=/junit-reports/pytest-junit-report.xml --cov=jibrel --cov-report xml:/coverage-reports/pytest-coverage-report.xml',
                                'pytest -c jibrel_admin/pytest.ini --junitxml=/junit-reports/pytest-admin-junit-report.xml --cov=jibrel --cov-report xml:/coverage-reports/pytest-admin-coverage-report.xml',
                        ],
                ]
        ],
)
