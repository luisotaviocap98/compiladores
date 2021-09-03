from anytree.exporter.dotexporter import UniqueDotExporter
import tppparser
from sys import argv
import math
from mytree import MyNode

nodeNewRoot = None
tempCabecalhoFunc = None
ParentTree = list()
list_parents = list()
list_terminal= list()
list_semantic= list()
n_used_func  = list()
list_func_checked= list()
list_func_declared= set()
list_vars_declared= set()
node_list_parents = list()
node_list_terminal= list()
list_func_no_return = set()
list_var_inicializada = list()
ignorar = ["vazio",","]
criarPai = ["var","numero"]    

def percorre(arvore):
    if len(arvore.children)>0: #se tiver filihos
        list_parents.append(arvore)
        for i in arvore.children:
            percorre(i) #percorrendo a arvores para os filhos de um nó
    else:
        list_terminal.append(arvore) #se for um simbolo terminal

def percorre_node(node):
    node_list_parents.clear() # para armazenarem apenas as informacoes de um nó passado, sem acumular de todos nós da arvore
    node_list_terminal.clear()
    walk_node(node)
    
def walk_node(node):
    if len(node.children)>0: 
        node_list_parents.append(node)
        for i in node.children:
            walk_node(i) 
    else:
        node_list_terminal.append(node) 


def main_rule():
    for i in list_terminal:
        if i.name == "principal": #achar nó que referencia a funçao main
            if i.parent.parent.name != "chamada_funcao":
                tipo = i.parent.parent.parent.children[0].children[0].children[0] #adicionando o tipo da funcao
                node = i # nó da principal
                escopo = i.name #escopo
                list_principal = [tipo,node,-1,"global",escopo,"funcao","global"]
                list_semantic.append(list_principal.copy()) #adicionando a funcao a lista das valors semanticas
                funcoes_rule(i.parent.parent,i.name)
                return
    print("ERROR: Função principal não declarada")   

def funcoes_rule(func,func_name):
    if func == -1:
        print("ERROR: Função \033[1m{}\033[0m não declarada".format(func_name))
        return -1
    
    for i in list_func_checked: #funcao já verificada
        if i[0]==func_name:
            return i[1]
    
    tem_retorno = False
    
    for i in func.children:
        if i.name == "corpo":
            percorre_node(i) #pegar informações dos nós filhos do corpo
            for j in node_list_parents.copy():
                if j.name == "retorna":
                    tem_retorno = True
                    if j.parent.parent.parent.name == "cabecalho": #funcao retorna desse mesmo corpo
                        percorre_node(j)
                        for k in node_list_parents.copy():
                            if k.name == "expressao":
                                percorre_node(k)
                                for l in node_list_terminal.copy():
                                    retorno  = ""
                                    if l.parent.parent.name == "numero":
                                        retorno = l.parent.name #recuperando qual o tipo da variaval que esta retornando
                                        retorno = retorno.split('_')[1].lower()
                                    elif l.parent.name == "ID":
                                        retorno = variavel_declarada(l,func_name) #recuperando qual o tipo da variaval que esta retornando
                                    if retorno != "" and retorno != -1:
                                        tipo_func = func.parent.children[0].children[0].children[0].name 
                                        if retorno != tipo_func: #se varivel e tipo da funcao forem diferentes
                                            func_tem_tipo = (func.parent.children[0].name != "cabecalho") #se o primeiro / unico filho for o cabecalho é pq eh void
                                            print('ERROR: Função \033[1m{}\033[0m do tipo \033[1m{}\033[0m retornando tipo \033[1m{}\033[0m'.format(func_name,(tipo_func if func_tem_tipo else "vazio"),retorno))
                                    
                                        list_func_checked.append([func_name,tipo_func])
                                        return             
                    
    if tem_retorno == False and func.parent.children[0].name == "tipo": #se a funcao tem tipo
        if func not in list_func_no_return:
            list_func_no_return.add(func)
            list_func_checked.append([func_name,-1])
            
            print('ERROR: Função \033[1m{}\033[0m do tipo \033[1m{}\033[0m não possui retorno'.format(func_name,func.parent.children[0].children[0].children[0].name))
            return                    
                  
def get_func(name):
    for i in list_parents:
        if i.name == "declaracao_funcao":
            for j in i.children:
                if j.name == "cabecalho":
                    if j.children[0].children[0].name == name:
                        return j #retorna o nó que referencia o cabecalho funcao
    return -1                  
                   
                   
def func_param_count(node): #percorre a partir do cabecalho ou chamada funcao
    # count = 0
    count = 0
    for i in node.children:
        if i.name == "lista_parametros": #percorre os parametros na declaracao da funcao
            percorre_node(i)
            
            for j in node_list_parents:
                if j.name == "parametro":
                    count += 1
            return count
        
    count = 0
    for i in node.children:
        if i.name == "lista_argumentos":
            percorre_node(i)
            if i.children[0].name != 'vazio':
                count += 1

                for j in node_list_parents: #percorre os argumentos na chamada da funcao
                    if j.name == 'VIRGULA': #se achar a virgula significa que tem mais coisa
                        x = func_that_called(None,j)
                        if x == node.children[0].children[0]: #a funcao que chamou precisa ser a mesma, para n ser outra funcao de chamada
                            count += 1
            return count
                           
    return count


def func_that_called(func,node):
    if node.name != 'chamada_funcao':
        func = func_that_called(None,node.parent)
    else:
        func = node.children[0].children[0]
    return func

def cabecalho_funcao(node):
    global tempCabecalhoFunc
    tempCabecalhoFunc = None
    cabecalho_funcao_recursive(node)
    
def cabecalho_funcao_recursive(node):
    if node.name == "cabecalho":
        global tempCabecalhoFunc
        tempCabecalhoFunc = node #pegar o nó que contem todo o cabeçalho
        return
    else:
        if node.parent.name != "programa":
            cabecalho_funcao(node.parent)
        return

                
def funcoes_param_compare():
    for i in list_parents:
        if i.name == "chamada_funcao": #encontrando todas chamadas de função
            if i.children[0].children[0].name == "principal":
                print('WARN: Chamada indevida da função principal')
            else:
                has_retorno_func = funcoes_rule(get_func(i.children[0].children[0].name),i.children[0].children[0].name)
                if has_retorno_func != -1:
                    numParamOriginFunc = func_param_count(get_func(i.children[0].children[0].name)) #quantidade de parametros declarados
                    numParamCallFunc = func_param_count(i)                                          #quantidade de parametros passados
                    if numParamOriginFunc != numParamCallFunc:
                        print('ERROR: Função \033[1m{}\033[0m recebe \033[1m{}\033[0m parâmetros, mas foram passados \033[1m{}\033[0m'.format(i.children[0].children[0].name,numParamOriginFunc,numParamCallFunc))
            for j in i.children:
                if j == "lista_argumentos":
                    percorre_node(j)
                    for k in node_list_terminal:
                        if k not in list_terminal:
                            print('ERROR: Variável \033[1m{}\033[0m na função \033[1m{}\033[0m não existe'.format(i.children[0].children[0].name,k.name))


def funcao_declarada():
    funcao_info = [0,0,-1,"global","global","funcao","global"]
    for i in list_parents:
        if i.name == "declaracao_funcao": #buscando por funcao declarada
            if i.children[0].children[0].name != "ID": #se for funcao com tipo
                if i.children[1].children[0].children[0].name != "principal": #se tem tipo e não é a funcao "principal"
                    funcao_info[0] = i.children[0].children[0].children[0]      #tipo
                    funcao_info[1] = i.children[1].children[0].children[0]      #referenci a funcao
                    funcao_info[4] = i.children[1].children[0].children[0].name #nome da funcao
                    list_semantic.append(funcao_info.copy())
                    list_func_declared.add(funcao_info[1])
            else: #funcao sem tipo
                if i.children[0].children[0].children[0].name != "principal": #se não tem tipo e não é a funcao "principal"
                    funcao_info[0] = "vazio"
                    funcao_info[1] = i.children[0].children[0].children[0]
                    funcao_info[4] = i.children[0].children[0].children[0].name
                    list_semantic.append(funcao_info.copy())
                    list_func_declared.add(funcao_info[1]) #para nao adicionar repetidos
    func_not_used()

def func_not_used():
    n_used_func = set(list_func_declared.copy())
    for i in list_terminal:
        for j in n_used_func.copy():
            if i.name == j.name:
                if i.parent.parent.parent != j.parent.parent.parent: #removendo as funcoes que foram chamadas/utilizadas
                    n_used_func.remove(j)
    
    for i in n_used_func:
        print('WARN: Função \033[1m{}\033[0m declarada, mas não utilizada'.format(i.name))
        funcoes_rule(i.parent.parent,i.name)

        
def declaracao_variavel():
    for i in list_parents:
        if i.name == "declaracao_variaveis": #se for uma declaracao de variavel
            if i.parent.name == "declaracao": #declaracao global
                escopo_ref = escopo = "global"
            else:
                escopo_ref = "local" #declaracao dentro de uma funcao
                escopo = escopo_da_variavel(i)
            temp = ["type","variable",-1,escopo_ref,escopo,"variável","expressao"]
            for j in i.children:
                if j.name == "lista_variaveis": #pegar as variaveis
                    percorre_node(j)
                    temp[0] = i.children[0].children[0].children[0]
                    for k in node_list_parents:
                        if 'indice' not in node_list_parents:
                            if k.name == "ID": #acha o nome das variaveis
                                list_vars_declared.add(k.children[0]) #nome da variavel
                                temp[1] = k.children[0]
                                multi_declaracao_variavel(temp)
                                list_semantic.append(temp.copy())
                        else:                    
                            if k.name == "ID": #acha o nome das variaveis
                                list_vars_declared.add(k.children[0]) #nome da variavel
                                temp[1] = k.children[0]
                                
                            if k.name == "indice": #se for um array 
                                temp[2] = check_indice(k,k.parent.children[0].children[0].name)
                            list_semantic.append(temp.copy())
                            multi_declaracao_variavel(temp)
            
        if i.name == "parametro":
            if i.parent.name == "lista_parametros":
                tipo = i.children[0].children[0].children[0]
                var = i.children[2].children[0]
                escopo = escopo_da_variavel(i)
                temp = [tipo,var,-1,"local",escopo,"variável","parâmetro"]
                multi_declaracao_variavel(temp)
                list_semantic.append(temp.copy())
    
    variavel_nao_usada()


def escopo_da_variavel(node):
    cabecalho_funcao(node)
    if tempCabecalhoFunc != None:
        return tempCabecalhoFunc.children[0].children[0].name
    else:
        return "global"

def multi_declaracao_variavel(obj):
    for i in list_semantic:
        if i[1].name == obj[1].name: #se encontra a variavel na lista de semantica
            if i[3] == obj[3]: #se esta declarada no mesmo escopo
                if i[4] == obj[4]:
                    print('WARN: Variável \033[1m{}\033[0m já foi declarada'.format(obj[1].name))

def check_indice(node,name):
    percorre_node(node)
    for i in node_list_parents:
        if i.name == "numero": #achar o nó que diz que o indice é um numero
            if i.children[0].name == "NUM_PONTO_FLUTUANTE":
                print("Erro: índice do array \033[1m{}\033[0m não é um inteiro".format(name))
            return i.children[0].children[0] #retorna o numero
            
    
    if node.parent.parent.parent.children[0].name != "tipo":
        print('WARN: Array \033[1m{}\033[0m não possui tipo'.format(name))
    
    return -1  

def variavel_nao_usada():
    used = set()
    for i in list_terminal:
        for j in list_vars_declared:
            if i.name == j.name: #se encontrar a variavel
                if i.parent.parent.parent != j.parent.parent.parent: #se estiver sendo usada em locais diferentes
                    used.add(j)  
    
    for i in list_vars_declared.difference(used):
        print('WARN: Variável \033[1m{}\033[0m declarada mas não utilizada'.format(i.name))


def tem_atribuicao():
    for i in list_parents:
        if i.name == "atribuicao": #acha atribuicao de variavel
            percorre_node(i)
            cabecalho_funcao(i)
            
            temp = list()
            hasFunc = False
            for find in node_list_parents:
                if find.name == "chamada_funcao":
                    hasFunc = True
                if find.name == "indice":
                    hasFunc = True
                    indice_valido(find.parent)
                    
            for j in node_list_parents:
                if j.name == "ID":
                    if tempCabecalhoFunc != None: #se a variavel estiver dentro de uma funcao
                        temp.append([j.children[0],tempCabecalhoFunc.children[0].children[0].name])
                    else:
                        temp.append([j.children[0],"global"])
                    list_var_inicializada.append(temp[0]) #adiciona como uma variavel que foi inicializada
                elif j.name == "numero" and not hasFunc: 
                        if tempCabecalhoFunc != None:
                            temp.append([j.children[0],tempCabecalhoFunc.children[0].children[0].name])
                        else:
                            temp.append([j.children[0],"global"])
            check_tipo_var(temp)
      
        if i.name == 'leia':
            cabecalho_funcao(i)
            for j in i.children:
                if j.name == 'var':
                    temp = list()
                    if tempCabecalhoFunc != None: #se a variavel estiver dentro de uma funcao
                        temp.append([j.children[0].children[0],tempCabecalhoFunc.children[0].children[0].name])
                    else:
                        temp.append([j.children[0].children[0],"global"])
                    list_var_inicializada.append(temp[0]) #adiciona como uma variavel que foi inicializada
                    check_tipo_var(temp)
                    
            
def indice_valido(node):
    for i in list_semantic:
        if node.children[0].children[0].name == i[1].name: #acha o nó referente ao nome da variavel
            percorre_node(node)
            for j in node_list_parents:
                if j.name == "numero": #acha onde tem o numero do indice
                    if float(j.children[0].children[0].name) > float(i[2].name): #se o numero atual for maior do que o na declaracao
                        print('ERROR: Índice \033[1m{}\033[0m do array \033[1m{}\033[0m está fora do intervalo'.format(j.children[0].children[0].name,i[1].name))
                    return

def check_tipo_var(obj):
    types = get_type_var(obj)
    count = 0
    
    if types == -1:
        return
    
    for i in types:
        if i == None:
            print('ERROR: Variável \033[1m{}\033[0m não declarada'.format(obj[count][0].name))
            return
        count += 1
    
    count = 0
    
    for i in range(len(types) - 1):
        if types[count] != types[count + 1]:
            if obj[count + 1][0].parent.name != "numero": #se o que esta recebendo nao é um numero
                print("WARN: Coerção -> Atribuição de tipos distintos \033[1m{}\033[0m \033[1m{}\033[0m e \033[1m{}\033[0m \033[1m{}\033[0m ".format(obj[count][0].name,types[count],obj[count + 1][0].name,types[count + 1]))
            elif obj[count][0].parent.name == "numero" and obj[count + 1][0].parent.name == "numero": #se sao variaveis numericas
                print("WARN: Coerção -> Atribuição de tipos distintos numero \033[1m{}\033[0m e numero \033[1m{}\033[0m ".format(types[count],types[count + 1]))
            else: #se sao coisas de tipo diferente (ex: array e funcao)
                print("WARN: Coerção -> Atribuição de tipos distintos \033[1m{}\033[0m \033[1m{}\033[0m e \033[1m{}\033[0m \033[1m{}\033[0m ".format(obj[count][0].name,types[count],obj[count + 1][0].parent.name,types[count + 1]))
        count += 1            


def get_type_var(obj):
    verify = [False]*(len(obj)) #inicializar lista
    types = [None]*(len(obj))
    count = 0

    if len(obj) <= 1: #precisa mandar o ID e o que esta sendo atribuido
        return -1

    for i in obj:
        if i[0].parent.name == "numero": 
            if i[0].name == "NUM_INTEIRO":
                types[count] = "inteiro"
            elif i[0].name == "NUM_PONTO_FLUTUANTE":
                types[count] = "flutuante"
        count += 1
    
    count = 0

    for i in list_semantic:
        if i[1].name == obj[0][0].name: #primeiro atributo
            if i[4] == obj[0][1] and types[0] == None: #declaradas mesmo escopo e nao é um numero
                types[0] = i[0].name
                verify[0] = True
        if i[1].name == obj[1][0].name: #segundo atributo
            if i[4] == obj[1][1] and types[1] == None:
                types[1] = i[0].name
                verify[1] = True
                
    for i in verify:
        if i == False:
            for j in list_semantic:
                if j[1].name == obj[count][0].name: #se for da mesma funcao
                    types[count] = j[0].name #recebe o nome do tipo da funcao
        count += 1
    return types


def variavel_declarada(var,escopo):
    for i in list_semantic:
        if i[1].name == var.name and (i[4] == escopo or i[4] == "global"):
            return i[0].name #retornar o tipo da variavel
    print('WARN: Variável \033[1m{}\033[0m no escopo \033[1m{}\033[0m não foi declarada'.format(var.name,escopo))
    return -1

def check_escreva():
    for i in list_parents:
        if i.name == "escreva": #acha a funcao escreva
            cabecalho_funcao(i)
            for j in i.children:
                if j.name == "expressao": #a expressao dentro do escreva
                    percorre_node(j)
                    for k in node_list_terminal:
                        if k.parent.name == "ID":
                            if tempCabecalhoFunc == None: #se teve uma funcao que invocou ele
                                variavel_not_inicializada(k,"global")
                            else:
                                variavel_not_inicializada(k,tempCabecalhoFunc.children[0].children[0].name)

def variavel_not_inicializada(variable,scope):
    for i in list_var_inicializada:
        if i[0].name == variable.name:
            if i[1] == scope or i[1] == "global": #se a variavel foi inicializada em algum escopo
                return 0
    
    for i in list_semantic:
        if i[1].name == variable.name:
            if i[5] == "funcao":
                return 0
            
    print('WARN: Variável \033[1m{}\033[0m declarada mas não inicializada'.format(variable.name))
    return -1



def print_tabela():
    
    print("\n======================================== TABELA ===========================================\n")
    print('|{:^6}| |{:^10}| |{:^8}| |{:^20}| |{:^20}| |{:^9}|'.format('ESCOPO','DECLARACAO','TAG','LOCAL','NOME','TIPO'))
    print("-------------------------------------------------------------------------------------------")
    
    for i in list_semantic:
        if i[0] == "vazio":
            print("|{:^6}| |{:^10}| |{:^8}| |{:^20}| |{:^20}| |{:^9}|".format(i[3],i[6],i[5],i[4],i[1].name,i[0]))
        else:
            print("|{:^6}| |{:^10}| |{:^8}| |{:^20}| |{:^20}| |{:^9}|".format(i[3],i[6],i[5],i[4],i[1].name,i[0].name))
    print("\n===========================================================================================\n")

def MainRoot():
    global nodeNewRoot
    nodeNewRoot = MyNode(name='programa', type='PROGRAMA') #criar o primeiro nó, representando o programa
    programa = nodeNewRoot
    return programa


def final_children(node): #pegar ultimo nó mais a esquerda
    if len(node.children) >0: #enquanto tiver filhos
        final_children(node.children[0])
    else:
        if node.name == "vazio":
            new_node = MyNode(name=node.parent.name)
            Tree_add_parent(new_node)
        else:
            Tree_add_parent(node)
        return 

def Tree_add_parent(node):
    ParentTree.clear()
    ParentTree.append(node)

def node_new_parent(name):
    caso1 = [0,True]
    caso2 = [1,True]
    caso3 = [1,False]
    default = [-1,False]
    opt = {
        "lista_declaracoes": caso1,
        "declaracao_funcao":caso1,
        "cabecalho": caso1,
        "numero": caso1,
        "var": caso1,
        "se": caso2,
        "leia":caso2,
        "corpo":caso2,
        "repita":caso2,
        "indice": caso2,
        "escreva": caso2,
        "retorna":  caso2,
        "parametro": caso2,
        "atribuicao": caso2,
        "chamada_funcao":caso2,
        "lista_variaveis":caso2,
        "lista_argumentos":caso2,
        "lista_parametros": caso2,
        "declaracao_variaveis":caso2,
        "expressao_aditiva": caso3,
    }
    return opt.get(name,default)

def arvore_reduce(node,parent):
    if len(node.children) > 1:
        count = 0
        values = node_new_parent(node.name)
        valor, mudar_parent = values[0], values[1]
        if valor == -1:
            valor = math.ceil(len(node.children)/2) -1 #valor do meio
            
        if mudar_parent: #se der para reduzir
            if node.name==parent.name: #exemplo: corpo -> corpo
                new_node = parent
            else:
                new_node = MyNode(name=node.name,parent=parent)
                
            parent = new_node
            Tree_add_parent(new_node)
        else:
            final_children(node.children[valor]) #pega folha do filho do meio; casos de atribuicao e declaracao
            ParentTree[0].parent = parent #adiciona o parent como pai do nó folha
            parent = ParentTree[0] #nó folha é o novo parent
        
        for i in node.children:
            if not mudar_parent:
                if count != valor:
                    arvore_reduce(i,parent) #rodando para reduzir; vai mudando o filho mas o pai continua
            else:
                arvore_reduce(i,parent)
            count += 1
    
    elif len(node.children) == 1:
        arvore_reduce(node.children[0], parent)
    
    else: #terminal
        if parent != None and node != None:
            if node.name not in ignorar:
                if node.parent.parent.name in criarPai:
                    if node.parent.parent.name == "numero":
                        node.parent =MyNode(name=node.parent.name, parent=parent)
                    else:
                        node.parent = parent
                else:
                    node.parent = parent

def tree_builder(root):
    try:
        arvore_reduce(root, MainRoot())
    except:
        print("ERROR: não foi possível gerar a Árvore Semântica")
    
    try:
        UniqueDotExporter(nodeNewRoot).to_picture(argv[1] + ".resume.unique.ast.png")
    except:
        0
        
def executar_tudo():
    declaracao_variavel()
    main_rule()
    funcao_declarada()
    tem_atribuicao()
    funcoes_param_compare()
    check_escreva()
    # print_tabela()

def main():
    arvore = None
    try:
        arvore = tppparser.main()
        percorre(arvore)
        executar_tudo()
        
    except:
        print("ERROR: não foi possível capturar as regras semânticas")
    
    tree_builder(arvore)
    
    return nodeNewRoot
    
if __name__ == "__main__":
    main()