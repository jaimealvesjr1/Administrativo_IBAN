$(document).ready(function() {

    // --- 1. SCRIPTS GLOBAIS ---

    /**
     * GLOBAL: Auto-dismiss alerts (de base/components/alerts.html)
     */
    setTimeout(() => {
        const alerts = document.querySelectorAll('.alert.auto-dismiss');
        alerts.forEach(alert => {
            // Verifica se a instância Bootstrap existe antes de fechar
            const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
            if (bsAlert) {
                bsAlert.close();
            }
        });
    }, 6000);

    /**
     * GLOBAL: Inicializa Select2 estáticos (sem busca AJAX)
     * Adicione a classe 'select2-static' em qualquer <select> que não precise de busca
     */
    $('.select2-static').select2({
        theme: 'bootstrap-5',
        minimumResultsForSearch: Infinity // Esconde a caixa de busca
    });
    
    /**
     * GLOBAL: Inicializa Select2 com busca local (sem AJAX)
     * Adicione a classe 'select2-searchable' em qualquer <select> com muitas opções
     */
    $('.select2-searchable').select2({
        theme: 'bootstrap-5'
    });
    
    // --- 2. SCRIPTS ESPECÍFICOS POR PÁGINA ---
    // (Usamos o ID de um elemento principal da página para rodar o script só onde ele é necessário)

    /**
     * PÁGINA: ctm/presenca.html (ID: #form-ctm-presenca)
     */
    const $formCtmPresenca = $('#form-ctm-presenca');
    if ($formCtmPresenca.length) {
        const buscarMembrosUrl = $formCtmPresenca.data('buscar-membros-url');
        
        $('#nome_aluno_select2').select2({
            placeholder: "Clique para buscar seu nome:",
            allowClear: true,
            width: '100%',
            theme: 'bootstrap-5', 
            ajax: {
                url: buscarMembrosUrl,
                dataType: 'json',
                delay: 250,
                data: function (params) {
                    return { term: params.term };
                },
                processResults: function (data) {
                    return { results: data.items };
                },
                cache: true
            }
        });

        $('#avaliacao').select2({
            theme: 'bootstrap-5',
            minimumResultsForSearch: Infinity 
        });
    }

    /**
     * PÁGINA: financeiro/registro_receita.html (ID: #form-registro-receita)
     */
    const $formReceita = $('#form-registro-receita');
    if ($formReceita.length) {
        const buscarMembrosUrl = $formReceita.data('buscar-membros-url');
        const campusValidos = JSON.parse($formReceita.data('campus-validos'));
        const idAnonimo = parseInt($formReceita.data('id-anonimo'));

        $('#membro_financeiro_select2').select2({
            placeholder: "Clique para buscar ou digite o nome do contribuinte",
            allowClear: true,
            width: '100%',
            theme: 'bootstrap-5',
            ajax: {
                url: buscarMembrosUrl,
                dataType: 'json',
                delay: 250,
                data: function (params) {
                    return { term: params.term };
                },
                processResults: function (data) {
                    return { results: data.items };
                },
                cache: true
            }
        });

        $('#tipo_select2, #forma_select2, #centro_custo_select').select2({
            theme: 'bootstrap-5',
            minimumResultsForSearch: Infinity,
            placeholder: function(){
                if ($(this).is('#centro_custo_select')) {
                    return "Selecione o Centro de Custo";
                }
                if ($(this).is('#tipo_select2')) {
                    return "Selecione o Tipo";
                }
                return $(this).data('placeholder');
            },
            allowClear: true
        });

        $('#membro_financeiro_select2').on('select2:select', function (e) {
            var data = e.params.data;
            if (data.id == idAnonimo) {
                $('#centro_custo_select').val('').trigger('change');
                $('#tipo_select2').val('Oferta').trigger('change');
            } else {
                var campusDoMembro = data.campus;
                if (campusDoMembro && campusValidos.includes(campusDoMembro)) {
                    $('#centro_custo_select').val(campusDoMembro).trigger('change');
                } else {
                    $('#centro_custo_select').val('').trigger('change');
                }
                $('#tipo_select2').val('').trigger('change');
            }
        });
        
        $('#membro_financeiro_select2').on('select2:unselect', function (e) {
            $('#centro_custo_select').val('').trigger('change');
            $('#tipo_select2').val('').trigger('change');
        });

        $('#valor_contribuicao').mask('000.000.000.000.000,00', {reverse: true});

        $formReceita.on('submit', function() {
            var valorFormatado = $('#valor_contribuicao').val();
            var valorNumerico = valorFormatado.replace(/\./g, '').replace(',', '.');
            $('#valor_contribuicao').val(valorNumerico);
        });
    }

    /**
     * PÁGINA: financeiro/registro_despesa.html (ID: #form-registro-despesa)
     */
    const $formDespesa = $('#form-registro-despesa');
    if ($formDespesa.length) {
        $('#item_despesa_select2').select2({
            allowClear: true,
            width: '100%',
            theme: 'bootstrap-5'
        });
        
        $('#centro_custo_despesa_select2').select2({
            theme: 'bootstrap-5',
            minimumResultsForSearch: Infinity,
            placeholder: "Selecione o Centro de Custo",
            allowClear: true
        });

        $('#valor_despesa').mask('000.000.000.000.000,00', {reverse: true});

        $formDespesa.on('submit', function() {
            var valorFormatado = $('#valor_despesa').val();
            var valorNumerico = valorFormatado.replace(/\./g, '').replace(',', '.');
            $('#valor_despesa').val(valorNumerico);
        });
    }

    /**
     * PÁGINA: financeiro/lancamentos_receitas.html (ID: #tipo_filtro_select2)
     */
    if ($('#tipo_filtro_select2').length) {
         $('#tipo_filtro_select2, #status_filtro_select2').select2({
            theme: 'bootstrap-5',
            minimumResultsForSearch: Infinity
        });
    }

    /**
     * PÁGINA: financeiro/lancamentos_despesas.html (ID: #categoria_filtro_select2)
     */
    if ($('#categoria_filtro_select2').length) {
        $('#categoria_filtro_select2').select2({
            theme: 'bootstrap-5',
            minimumResultsForSearch: Infinity,
            placeholder: "Selecione a Categoria",
            allowClear: true
        });
    }

    /**
     * PÁGINA: eventos/gerenciar_evento.html (ID: #membros_select2)
     */
    const $selectMembrosEvento = $('#membros_select2');
    if ($selectMembrosEvento.length) {
        const buscarMembrosUrl = $selectMembrosEvento.data('buscar-membros-url');
        const tipoEvento = $selectMembrosEvento.data('tipo-evento');
        const eventoId = $selectMembrosEvento.data('evento-id');
        
        $selectMembrosEvento.select2({
            placeholder: "Selecione membros para inscrever",
            allowClear: true,
            width: '100%',
            theme: 'bootstrap-5', // Adicionado tema
            ajax: {
                url: buscarMembrosUrl,
                dataType: 'json',
                delay: 250,
                data: function (params) {
                    return {
                        q: params.term,
                        tipo_evento: tipoEvento,
                        evento_id: eventoId
                    };
                },
                processResults: function (data) {
                    return { results: data.results };
                },
                cache: true
            }
        });
    }

    /**
     * PÁGINA: grupos/pgs/detalhes.html (ID: #membro_select2)
     */
    const $selectAddParticipante = $('#membro_select2');
    if ($selectAddParticipante.length) {
        const buscarMembrosUrl = $selectAddParticipante.data('buscar-membros-url');
        $selectAddParticipante.select2({
            placeholder: "Clique para buscar ou digite o nome do participante",
            allowClear: true,
            theme: 'bootstrap-5',
            ajax: {
                url: buscarMembrosUrl,
                dataType: 'json',
                delay: 250,
                data: function (params) {
                    return { term: params.term };
                },
                processResults: function (data) {
                    return { results: data.items };
                },
                cache: true
            }
        });
    }

    /**
     * PÁGINA: ctm/painel_facilitador.html (ID: #membro_id_select2)
     */
    const $selectAddAluno = $('#membro_id_select2');
    if ($selectAddAluno.length) {
        const buscarMembrosUrl = $selectAddAluno.data('buscar-membros-url');
        $selectAddAluno.select2({
            dropdownParent: $('#adicionarAlunoModal'), // Necessário por estar dentro de um modal
            theme: "bootstrap-5",
            placeholder: 'Pesquisar membro...',
            ajax: {
                url: buscarMembrosUrl,
                dataType: 'json',
                delay: 250,
                data: function (params) {
                    return { term: params.term };
                },
                processResults: function (data) {
                    return { results: data.items };
                },
                cache: true
            }
        });
    }

    /**
     * PÁGINA: auth/registrar_membro.html (ID: #membro_id_select2)
     */
    if ($('#membro_id_select2').length && !$('#membro_id_select2').data('ajax--url')) {
        $('#membro_id_select2').select2({
            placeholder: "Clique para buscar seu nome:",
            allowClear: true,
            width: '100%',
            theme: 'bootstrap-5',
        });
    }
    
    /**
     * PÁGINA: grupos/areas/form.html & grupos/setores/form.html (ID: #supervisores)
     */
    if ($('#supervisores').length) {
        $('#supervisores').select2({
            theme: "bootstrap-5",
            width: $( this ).data( 'width' ) ? $( this ).data( 'width' ) : $( this ).hasClass( 'w-100' ) ? '100%' : 'style'
        });
    }

    /**
     * PÁGINA: admin_users/list_users.html (ID: #confirmDeleteModal)
     */
    var confirmDeleteModal = document.getElementById('confirmDeleteModal');
    if (confirmDeleteModal) {
        confirmDeleteModal.addEventListener('show.bs.modal', function (event) {
            var button = event.relatedTarget;
            var userId = button.getAttribute('data-user-id');
            var userEmail = button.getAttribute('data-user-email');
            var deleteActionUrl = button.getAttribute('data-delete-url');

            var modalUserEmail = confirmDeleteModal.querySelector('#modalUserEmail');
            var deleteUserForm = confirmDeleteModal.querySelector('#deleteUserForm');

            modalUserEmail.textContent = userEmail;
            deleteUserForm.action = deleteActionUrl;
        });
    }
    
    /**
     * PÁGINA: membresia/cadastro.html (ID: #alerta-duplicidade)
     */
    const inputNomeCadastro = document.getElementById('nome_completo');
    const alertaDiv = document.getElementById('alerta-duplicidade');
    if (inputNomeCadastro && alertaDiv) {
        const sugestoesLista = document.getElementById('sugestoes-lista');
        const sugestoesUrl = $(inputNomeCadastro).data('sugestoes-url');
        let timeout = null;

        inputNomeCadastro.addEventListener('keyup', function() {
            clearTimeout(timeout);
            
            timeout = setTimeout(function() {
                const termoBusca = inputNomeCadastro.value.trim();
                if (termoBusca.length < 3) {
                    alertaDiv.style.display = 'none';
                    return;
                }

                fetch(`${sugestoesUrl}?q=${termoBusca}`)
                    .then(response => response.json())
                    .then(data => {
                        if (data.sugestoes.length > 0) {
                            sugestoesLista.innerHTML = '';
                            data.sugestoes.forEach(sugestao => {
                                const item = document.createElement('div');
                                item.innerHTML = `
                                    <div class="d-flex justify-content-between align-items-center">
                                        <span>
                                            <i class="bi bi-person-circle me-1"></i>
                                            <a href="${sugestao.perfil_url}" target="_blank">${sugestao.nome_completo}</a>
                                        </span>
                                        <small class="text-muted">
                                            <span class="badge bg-secondary me-1">${sugestao.status}</span>
                                            <span class="badge bg-info">${sugestao.campus}</span>
                                        </small>
                                    </div>
                                    <hr class="my-1">
                                `;
                                sugestoesLista.appendChild(item);
                            });
                            alertaDiv.style.display = 'block';
                        } else {
                            alertaDiv.style.display = 'none';
                        }
                    });
            }, 500);
        });
    }
    
    /**
     * PÁGINA: membresia/unificar_membros.html (ID: #unificar-form)
     */
    const $unificarForm = $('#unificar-form');
    if ($unificarForm.length) {
        const checkboxes = document.querySelectorAll('input[name="membros_ids[]"]');
        const unificarBtn = document.getElementById('unificar-btn');
        const revisarUrl = $unificarForm.data('revisar-url');

        function updateButtonState() {
            const checkedCount = Array.from(checkboxes).filter(cb => cb.checked).length;
            unificarBtn.disabled = checkedCount < 2;
            unificarBtn.innerText = `Avançar para Revisão (${checkedCount} selecionados)`;
        }

        checkboxes.forEach(checkbox => {
            checkbox.addEventListener('change', updateButtonState);
        });

        unificarBtn.addEventListener('click', function() {
            const checkedBoxes = Array.from(checkboxes).filter(cb => cb.checked);
            const membroIds = checkedBoxes.map(cb => parseInt(cb.value));
            
            if (membroIds.length < 2) {
                Swal.fire('Atenção', 'Selecione pelo menos dois membros para unificar.', 'warning');
                return;
            }

            fetch(revisarUrl, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ membros_ids: membroIds })
            })
            .then(response => {
                if (response.ok) {
                    return response.text();
                } else {
                    return response.json().then(error => { throw new Error(error.message); });
                }
            })
            .then(html => {
                document.open();
                document.write(html);
                document.close();
            })
            .catch(error => {
                Swal.fire('Erro', error.message, 'error');
            });
        });
    }
    
    /**
     * PÁGINA: ctm/listagem_unificada.html & grupos/listagem_unificada.html
     */
    if ($('#ctmTabs').length) {
        var tipoSelecionado = $('#ctmTabs').data('tipo-selecionado');
        if (tipoSelecionado) {
            $('#' + tipoSelecionado + '-tab').tab('show');
        }
    }
    if ($('#groupTabs').length) {
        var tipoSelecionado = $('#groupTabs').data('tipo-selecionado');
        if (tipoSelecionado) {
            $('#' + tipoSelecionado + '-tab').tab('show');
        }
    }

});
