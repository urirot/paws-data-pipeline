import os

from scripts import load_paws_data, match_data, create_master_df
from config import CURRENT_SOURCE_FILES_PATH, LOGS_PATH
from flask import current_app

MAPPING_FIELDS = {
    'salesforcecontacts': {
        '_label': 'salesforce',
        'table_id': 'contact_id',
        'table_email': 'email',
        '_table_name': ['first_name', 'last_name']
    },
    'petpoint': {
        '_label': 'petpoint',
        'table_id': 'outcome_person_#',
        'table_email': 'out_email',
        '_table_name': ['outcome_person_name']
    },
    'volgistics': {
        '_label': 'volgistics',
        'table_id': 'Number'.lower(),
        'table_email': 'Email'.lower(),
        '_table_name': ['first_name_last_name']
    }
}  # TODO: consider other important fields, such as phone number


def start_flow():
    if os.listdir(CURRENT_SOURCE_FILES_PATH):
        pandas_tables = dict()
        for uploaded_file in os.listdir(CURRENT_SOURCE_FILES_PATH):
            file_path = os.path.join(CURRENT_SOURCE_FILES_PATH, uploaded_file)
            file_name_striped = file_path.split('/')[-1].split('-')[0]
            current_app.logger.info('running load_paws_data on: ' + uploaded_file)
            db_engine = load_paws_data.load_to_postgres(file_path, file_name_striped, True)
            pandas_tables[file_name_striped] = match_data.read_from_postgres(db_engine, file_name_striped)
            pandas_tables[file_name_striped] = match_data.cleanup_and_log_table(pandas_tables[file_name_striped],
                MAPPING_FIELDS[file_name_striped],
                                                                                'excluded_' + file_name_striped + '.csv')

        with db_engine.connect() as connection:
            create_master_df.main(connection)


        matched_df = (
            pandas_tables['salesforcecontacts']
                .pipe(match_data.match_cleaned_table, pandas_tables['volgistics'], 'volgistics', 'unmatched_volgistics.csv')
        )

        matched_df.to_csv(os.path.join(LOGS_PATH, 'matches.csv'), index=False)

        # db_engine.dispose()  # we could close the db engine here once we're done with everything, but then it will be completely closed
        # See https://docs.sqlalchemy.org/en/13/core/connections.html#engine-disposal for design considerations.
