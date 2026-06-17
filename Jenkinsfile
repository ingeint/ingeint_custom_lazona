pipeline {
    agent none
    stages {

        stage('Clone and Copy module') {
            agent {
                label "$node"
            }
            environment {
                CONTAINER = sh(returnStdout: true, script: 'docker ps --filter "name=$CONTAINER_NAME" --latest --format "{{.ID}}"').trim()
                ADDON_PATH = "/mnt/extra-addons/"
                ADDON_FOLDER = "/tmp/addons"
            }
            steps {
                sh 'docker exec -u root $CONTAINER rm -rf ${ADDON_PATH}${PROJECT_NAME}'
                sh 'docker cp ${PROJECT_NAME} $CONTAINER:$ADDON_PATH${PROJECT_NAME}'
            }
        }
        stage('Update DB') {
            agent {
                docker {
                    image 'postgres:13'
                    label "$node"
                }
            }
            steps {
                withCredentials([usernamePassword(credentialsId: 'qaserver-odoo-creds', passwordVariable: 'pass', usernameVariable: 'user')]) {
                    sh 'export PGPASSWORD="$pass"; export PGUSER=odoo; psql -h "$ODOO_DB_SERVER" -p "$ODOO_DB_PORT" -U odoo -d "$DB_NAME" -c "update ir_module_module set state = \'to upgrade\' where name in (\'$ACTIVE_MODULES\')"'
                }
            }
        }
        stage('Restart Container'){
            agent {
                label "$node"
            }
            environment {
                CONTAINER = sh(returnStdout: true, script: 'docker ps --filter "name=$CONTAINER_NAME" --latest --format "{{.ID}}"').trim()
            }
            steps {
                sh 'docker rm -f $CONTAINER'
            }
        }
    }
}
