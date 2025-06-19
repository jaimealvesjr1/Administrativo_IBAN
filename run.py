from app import create_app
from app.extensions import db
from flask_migrate import Migrate

from app.membresia.models import Membro
from app.ctm.models import Aula, Presenca
from app.financeiro.models import Contribuicao

app = create_app()

migrate = Migrate(app, db)

#if __name__ == '__main__':
#    app.run(debug=True, host='0.0.0.0')
