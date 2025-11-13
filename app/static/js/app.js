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
    
    // --- FIM DOS SCRIPTS GLOBAIS ---
    // (Todo o resto foi removido e será colocado nos arquivos HTML)

});
