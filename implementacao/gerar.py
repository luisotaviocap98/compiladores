from llvmlite import ir
from llvmlite import binding as llvm
from llvmlite.binding import value
from llvmlite.ir.types import IntType
import semantica
from mytree import MyNode

varRecebe = None
retorno_func = None
current_scope = None
list_parents = list()
list_terminal = list()
node_list_parents = list()
node_list_terminal = list()
list_var_local = {'':{'':None}}
list_func_declarada = {'':[]}
list_vars_global = {}
op_aritmeticos = ['+','-','/','*']
op_comparadores = ['<','>','=','<=','>=','!=']
op_logico = ['<','>','=','<=','>=','!=','&&','||']
tipos_primitivos = ['NUM_INTEIRO','NUM_PONTO_FLUTUANTE']

# Código de Inicialização.
llvm.initialize()
llvm.initialize_all_targets()
llvm.initialize_native_target()
llvm.initialize_native_asmprinter()

# Cria o módulo.
module = ir.Module('modulo_LO.bc')
module.triple = llvm.get_process_triple()
target = llvm.Target.from_triple(module.triple)
target_machine = target.create_target_machine()
module.data_layout = target_machine.target_data

escrevaInteiro = ir.Function(module,ir.FunctionType(ir.VoidType(), [ir.IntType(32)]),name="escrevaInteiro")
escrevaFlutuante = ir.Function(module,ir.FunctionType(ir.VoidType(),[ir.FloatType()]),name="escrevaFlutuante")

leiaInteiro = ir.Function(module,ir.FunctionType(ir.IntType(32),[]),name="leiaInteiro")
leiaFlutuante = ir.Function(module,ir.FunctionType(ir.FloatType(),[]),name="leiaFlutuante")


def percorre(arvore):
    if len(arvore.children) > 0:  # se tiver filihos
        list_parents.append(arvore)
        for i in arvore.children:
            percorre(i)  # percorrendo a arvores para os filhos de um nó
    else:
        list_terminal.append(arvore)  # se for um simbolo terminal


def montar(node):
    if node.name == 'lista_declaracoes':
        for i in node.children:
            if i.name == 'declaracao_funcao':
                gerarFuncao(i)
            elif i.name == 'cabecalho':
                gerarFuncaoVazia(i)
            elif i.name == 'declaracao_variaveis':
                func_declaracao_varGlobal(i)
            elif i.name == 'atribuicao':
                func_atribuicaoGlobal(i)  # se existir variavel global
    else:
        for i in node.parent.children:
            if i.name == 'declaracao_funcao':
                gerarFuncao(i)
            elif i.name == 'cabecalho':
                gerarFuncaoVazia(i)
            elif i.name == 'declaracao_variaveis':
                func_declaracao_varGlobal(i)
            elif i.name == 'atribuicao':
                func_atribuicaoGlobal(i)  # se existir variavel global
        

#TODO
def func_se(node,bloco):
    # if_block = bloco.append_basic_block(name="if")
    # else_block = bloco.append_basic_block(name="else")
    if node.children[0].name == 'se':
        condicao = node.children[1]
        resolveLogica(condicao,bloco)
        # bloco.entry_builder.cbranch(xp[0], if_block, else_block)
        # bloco.position_at_end(if_block)

    
    if node.children[2].name == 'então':
        entao = node.children[3]
        for i in entao.children:
            map_func_especial.get(i.name)(i,bloco)
        # bloco.branch(else_block)
           
    if node.children[4].name == 'senão':
        senao = node.children[5]
        for i in senao.children:
            map_func_especial.get(i.name)(i,bloco)
        # bloco.position_at_end(else_block)
        # bloco.branch(else_block)
        

def resolveLogica(node,bloco):
    global module
    global current_scope

    if node.name in op_logico:
        exp1,tipo1 = resolveLogica(node.children[0],bloco)
        # print('retorno1 ',exp1,tipo1)
        exp2,tipo2 = resolveLogica(node.children[1],bloco)
        # print('retorno2 ',exp2,tipo2)
        return [func_logica(node.name,str(tipo1),str(tipo2),exp1,exp2,bloco),tipo2 if (str(tipo2) == 'i32' and str(tipo1) == 'i32')  else (tipo1 if str(tipo1) != 'i32' else tipo2)]
    
    elif node.name in tipos_primitivos:
        typeVar = ir.IntType(32) if node.name == 'NUM_INTEIRO' else ir.FloatType()
        valor = (int(node.children[0].name)) if node.name == 'NUM_INTEIRO' else (float(node.children[0].name))
        return [ir.Constant(typeVar,valor),typeVar]

    elif node.name == 'chamada_funcao': 
        return resolveCallFunction(node,bloco)
    
    elif node.name == 'var': 
        if node.children[1].name =='indice':
            return getArray(node,bloco)
    
    if node.name in op_aritmeticos:
        return resolveExpressao(node, bloco)
    
    else:
        return getVariavel(node,bloco)

def func_logica(operacao,tipo1,tipo2,exp1,exp2,bloco):
    if operacao in op_comparadores:
        if operacao == '=':
            operacao = '=='
            
        if tipo1 == tipo2 == 'i32':
            return bloco.icmp_signed(operacao,exp1,exp2)
        else:
            return bloco.fcmp_ordered(operacao,exp1,exp2)
        
    elif operacao == '&&':
        return bloco.and_(exp1,exp2)
    
    elif operacao == '||':
        return bloco.or_(exp1,exp2)
    
    
def func_leia(node,bloco):
    global module
    global current_scope
    
    if node.children[2].name == 'var': 
        if node.children[2].children[1].name == 'indice':
            varRef, varType = setArray(node.children[2],bloco)
            
    else:
        varRef, varType = setVariavel(node.children[2],bloco)
    
    
    funcLeia =  leiaInteiro if varType == ir.IntType(32) else leiaFlutuante    
    resultado_leia = bloco.call(funcLeia, args=[])
    bloco.store(resultado_leia, varRef)


def resolveCallFunction(node,bloco):
    global current_scope
    func = list_func_declarada.get(node.children[0].name)
    funcRef = func[0]
    funcParam = func[1] 
    TypeFunc = func[2]
    args = list()
    
    if node.children[2].name == 'lista_argumentos':
        for i in node.children[2].children:
            if i.name in tipos_primitivos:
                varType = ir.IntType(32) if i.name == 'NUM_INTEIRO' else ir.FloatType()
                valor = (int(i.children[0].name)) if i.name == 'NUM_INTEIRO' else (float(i.children[0].name))
                args.append(ir.Constant(varType,valor))
            
            elif i.name == 'chamada_funcao':
                args.append(resolveCallFunction(i,bloco)[0])
            
            elif i.name == 'var':
                if i.children[1].name == 'indice':
                    args.append(getArray(i,bloco)[0])
            
            else:
                args.append(getVariavel(i,bloco)[0])
                
    elif node.children[2].name not in ['(',')']:
        i = node.children[2]
        if i.name in tipos_primitivos:
            varType = ir.IntType(32) if i.name == 'NUM_INTEIRO' else ir.FloatType()
            valor = (int(i.children[0].name)) if i.name == 'NUM_INTEIRO' else (float(i.children[0].name))
            args.append(ir.Constant(varType,valor))

        elif i.name == 'chamada_funcao':
            args.append(resolveCallFunction(i,bloco)[0])

        elif i.name == 'var':
            if i.children[1].name == 'indice':
                args.append(getArray(i,bloco)[0])

        else:
            args.append(getVariavel(i,bloco)[0])        

    return [bloco.call(funcRef,args),TypeFunc]


def func_escreva(node,bloco):
    global module
    global current_scope
    isVar = False
    array = False
    array2D = False
    num = False
    
    i = node.children[2]
    if i.name == 'var': 
        if i.children[1].name == 'indice':
            varRef,varType = getArray(i,bloco)
            
    
    elif i.name in tipos_primitivos:
        varRef = ir.IntType(32)(int(i.children[0].name)) if i.name == 'NUM_INTEIRO' else ir.FloatType()(float(i.children[0].name))
        varType = ir.IntType(32) if i.name == 'NUM_INTEIRO' else ir.FloatType()
        
    
    elif i.name == 'chamada_funcao':
        varRef,varType = resolveCallFunction(i,bloco)
                
    else:
        varRef,varType = getVariavel(i,bloco)

    
    funcEscreva =  escrevaInteiro if varType == ir.IntType(32) else escrevaFlutuante
    
    
    bloco.call(funcEscreva,args=[varRef])
    

#TODO
def func_repita(node,bloco):
    global module
    global current_scope
    return


def func_retorna(node,bloco):
    global module
    global current_scope
    global retorno_func
    
    retorno = node.children[2]
    if retorno.name in op_aritmeticos:
        retorno_func = resolveExpressao(retorno,bloco)[0]
        
    elif retorno.name == 'chamada_funcao':
        retorno_func = resolveCallFunction(retorno,bloco)[0]
        
    elif retorno.name == 'var':
        if retorno.children[1].name == 'indice':
            retorno_func = getArray(retorno,bloco)[0]
            
    elif retorno.name in tipos_primitivos:
        varType = ir.IntType(32) if retorno.name == 'NUM_INTEIRO' else ir.FloatType()
        valor = (int(retorno.children[0].name)) if retorno.name == 'NUM_INTEIRO' else (float(retorno.children[0].name))
        retorno_func = ir.Constant(varType,valor)
        
    else:
        retorno_func = getVariavel(retorno,bloco)[0]
        
    
def getArray(node,bloco):
    global current_scope
    array = False
    array2D = False
    
    nome = node.children[0].name
    pos = int(node.children[1].children[1].children[0].name)
    if len(node.children[1].children) == 3:
        array = True
    else:
        pos2 = int(node.children[1].children[4].children[0].name)
        array2D = True
    
    var = list_var_local[current_scope].get(nome)
    if var == None:
        var = list_vars_global.get(nome)
    varType = var[0]
    varRef = var[1]
    
    if array:
        varRef = bloco.gep(varRef,[ir.IntType(32)(0),ir.IntType(32)(pos)])
    elif array2D:
        varRef = bloco.gep(varRef,[ir.IntType(32)(0),ir.IntType(32)(pos),ir.IntType(32)(pos2)])
    
    return [bloco.load(varRef, align=4),varType]
    
    
def setArray(node,bloco):
    global current_scope
    array = False
    array2D = False
    nome = node.children[0].name
    pos = int(node.children[1].children[1].children[0].name)
    if len(node.children[1].children) == 3:
        array = True
    else:
        pos2 = int(node.children[1].children[4].children[0].name)
        array2D = True
    
    var = list_var_local[current_scope].get(nome)
    if var == None:
        var = list_vars_global.get(nome)
    varType = var[0]
    varRef = var[1]
    
    if array:
        varRef = bloco.gep(varRef,[ir.IntType(32)(0),ir.IntType(32)(pos)])
    elif array2D:
        varRef = bloco.gep(varRef,[ir.IntType(32)(0),ir.IntType(32)(pos),ir.IntType(32)(pos2)])
    
    return [varRef,varType]
    
def getVariavel(node,bloco):
    global current_scope
    isParam = False
    
    var = list_var_local[current_scope].get(node.name)
    
    if var == None:
        var = list_vars_global.get(node.name)
    
    if var == None:
        args = list_func_declarada.get(current_scope)[0].args
        argsName = list_func_declarada.get(current_scope)[3]
        argsType = list_func_declarada.get(current_scope)[2]
        for i,j,k in zip(args,argsName,argsType):
            if node.name == j:
                isParam = True
                var = [k,i]
    
    typeVar = var[0] 
    varRef = var[1]
    
    if isParam:
        return [varRef,typeVar]
    return [bloco.load(varRef),typeVar]

def setVariavel(node,bloco):
    global current_scope
    var = list_var_local[current_scope].get(node.name)
    
    if var == None:
        var = list_vars_global.get(node.name)
    
    if var == None:
        args = list_func_declarada.get(current_scope)[0].args
        argsName = list_func_declarada.get(current_scope)[3]
        argsType = list_func_declarada.get(current_scope)[2]
        for i,j,k in zip(args,argsName,argsType):
            if node.name == j:
                var = [k,i]        # var = 
    
    typeVar = var[0] 
    varRef = var[1]
    return [varRef,typeVar]

def func_call_f(node,bloco):
    global module
    global current_scope
    resolveCallFunction(node,bloco)
    return


def func_calcular(operacao,tipo1,tipo2,exp1,exp2,bloco):
    if operacao == '+':
        if tipo1 == tipo2 == 'i32':
            return bloco.add(exp1,exp2)
        else:
            return bloco.fadd(exp1,exp2)
    if operacao == '-':
        if tipo1 == tipo2 == 'i32':
            return bloco.sub(exp1,exp2)
        else:
            return bloco.fsub(exp1,exp2)
    if operacao == '/':
        if tipo1 == tipo2 == 'i32':
            return bloco.div(exp1,exp2)
        else:
            return bloco.fdiv(exp1,exp2)
    if operacao == '*':
        if tipo1 == tipo2 == 'i32':
            return bloco.mul(exp1,exp2)
        else:
            return bloco.fmul(exp1,exp2)

def resolveExpressao(node,bloco):
    global module
    global current_scope

    if node.name in op_aritmeticos:
        exp1,tipo1 = resolveExpressao(node.children[0],bloco)
        # print('retorno1 ',exp1)
        exp2,tipo2 = resolveExpressao(node.children[1],bloco)
        # print('retorno2 ',exp2)
        return [func_calcular(node.name,str(tipo1),str(tipo2),exp1,exp2,bloco), tipo2 if (str(tipo2) == 'i32' and str(tipo1) == 'i32')  else (tipo1 if str(tipo1) != 'i32' else tipo2)]
    
    elif node.name in tipos_primitivos:
        typeVar = ir.IntType(32) if node.name == 'NUM_INTEIRO' else ir.FloatType()
        valor = (int(node.children[0].name)) if node.name == 'NUM_INTEIRO' else (float(node.children[0].name))
        return [ir.Constant(typeVar,valor),typeVar]
    

    elif node.name == 'chamada_funcao': 
        return resolveCallFunction(node,bloco)
    
    elif node.name == 'var': 
        if node.children[1].name =='indice':
            return getArray(node,bloco)
    
    else:
        return getVariavel(node,bloco)

def func_atribuicao(node,bloco):
    global module
    global current_scope
    varAtr,typeAtr = None,None
    
    if node.children[0].name == 'var':
        if node.children[0].children[1].name == 'indice':
            varAtr,typeAtr = setArray(node.children[0],bloco)
    else:
        varAtr,typeAtr = setVariavel(node.children[0],bloco)
    
    
    if node.children[2].name in tipos_primitivos:
        content = (int(node.children[2].children[0].name)) if node.children[2].name == 'NUM_INTEIRO' else (float(node.children[2].children[0].name))
        valor = ir.Constant(typeAtr, content)
    
    elif node.children[2].name == 'var':
        if node.children[2].children[1].name == 'indice':
            valor,typeVar = getArray(node.children[2],bloco)
    
    elif node.children[2].name == 'chamada_funcao':
        valor,typeVar = resolveCallFunction(node.children[2],bloco)

    
    elif node.children[2].name in op_aritmeticos:
        valor,_ = resolveExpressao(node.children[2],bloco)
        
    else:
        valor,typeVar = getVariavel(node.children[2],bloco)
    
    bloco.store(valor,varAtr)
        

#TODO
def atribuicaoNumGlobal(node):
    var = list_vars_global.get(node.children[0].name)
    typeVar = var[0] 
    varRef = var[1]
    value = int(node.children[2].children[0].name) if node.children[2].name == 'NUM_INTEIRO' else float(node.children[2].children[0].name) 
    #TODO pode ser retorno de funcao ou vetor
    varRef.initializer = ir.Constant(typeVar, value)
    varRef.linkage = 'dso_local'

#TODO
def atribuicaoArrayGlobal(node):
    var = list_vars_global.get(node.children[0].children[0].name)
    typeVar = var[0] 
    varRef = var[1]
    value = int(node.children[2].children[0].name) if node.children[2].name == 'NUM_INTEIRO' else float(node.children[2].children[0].name) 
    pos = int(node.children[0].children[1].children[1].children[0].name) if node.children[0].children[1].children[1].name == 'NUM_INTEIRO' else float(node.children[0].children[1].children[1].children[0].name) 
    # print(pos)
    # print(node.children[0].children[0].name,pos,value)
    # ptr = module.gep()
    # varRef.initializer = ir.Constant(typeVar, value)
    # varRef.linkage = 'dso_local'
    # return

#TODO
def atribuicaoArrayGlobal2D(node):
    return

def func_atribuicaoGlobal(node):
    if node.children[0].name == 'var':
        if node.children[0].children[1].name == 'indice':
            if len(node.children[0].children[1].children) > 3:
                atribuicaoArrayGlobal2D(node)
            else:
                atribuicaoArrayGlobal(node)
    else:
        atribuicaoNumGlobal(node)
    

def criarVarLocalArray2D(typeVar, nameVar, dimensoes,builder):
    global current_scope
    dim1=dimensoes[0]
    dim2=dimensoes[1]
    t = ir.ArrayType(typeVar, dim1)
    t2 = ir.ArrayType(t, dim2)
    var = builder.alloca(t2,name= nameVar)
    var.align = 4
    list_var_local[current_scope].update({nameVar:[typeVar,var]})

def criarVarLocalArray(typeVar, nameVar, size,builder):
    global current_scope
    t = ir.ArrayType(typeVar, size)
    var = builder.alloca(t,name= nameVar)
    var.align = 4
    list_var_local[current_scope].update({nameVar:[typeVar,var]})
    

def mountLocalArray(node,builder):
    typeVar = ir.IntType(32) if node.parent.children[0].name == 'inteiro' else ir.FloatType()
    nameVar = node.children[0].name
    for i in node.children:
        if i.name == 'indice':
            dimensao = int(len(i.children)/3)
            if dimensao > 1:
                dim_size = list()
                for j in i.children:
                    if j.name in ['NUM_INTEIRO','NUM_PONTO_FLUTUANTE']:
                        size = j.children[0].name
                        dim_size.append(int(size))
                criarVarLocalArray2D(typeVar, nameVar,dim_size,builder)
                dim_size.clear()
            else:
                if i.children[1].name in ['NUM_INTEIRO','NUM_PONTO_FLUTUANTE']:
                    size = i.children[1].children[0].name
                criarVarLocalArray(typeVar,nameVar,int(size),builder)
                
                
def criarVarLocal(node, typeVar, nameVar,builder):
    global current_scope
    var = builder.alloca(typeVar,name= nameVar)
    var.align = 4
    list_var_local[current_scope].update({nameVar:[typeVar,var]})
    

def func_declaracao_var(node,builder):
    typeVar = ir.IntType(32) if node.children[0].name == 'inteiro' else ir.FloatType()
    if node.children[2].name == 'lista_variaveis':
        for i in node.children[2].children:
            nameVar = i.name
            if nameVar == 'var':
                if i.children[1].name == 'indice':
                    mountLocalArray(i,builder)
            else:
                criarVarLocal(node, typeVar, nameVar,builder)
    elif node.children[2].name == 'var': #variavel array
        if node.children[2].children[1].name == 'indice':
            mountLocalArray(node.children[2],builder)
    else: #variavel normal
        nameVar = node.children[2].name
        criarVarLocal(node, typeVar, nameVar,builder)
    


def criarVarGlobal(node, typeVar, nameVar):
    global module
    var = ir.GlobalVariable(module, typeVar, nameVar)
    var.initializer = ir.Constant(typeVar, 0 if node.children[0].name == 'inteiro' else 0.0)
    var.linkage = "common"
    var.align = 4
    list_vars_global.update({nameVar:[typeVar,var]})


def criarVarGlobalArray(typeVar, nameVar, size):
    global module
    t = ir.ArrayType(typeVar, size)
    var = ir.GlobalVariable(module, t, nameVar)
    var.linkage = "common"
    var.initializer = ir.Constant(t, None)
    var.align = 4
    list_vars_global.update({nameVar:[typeVar,var]})
    

def criarVarGlobalArray2D(typeVar, nameVar, dimensoes):
    global module
    dim1=dimensoes[0]
    dim2=dimensoes[1]
    t = ir.ArrayType(typeVar, dim1)
    t2 = ir.ArrayType(t, dim2)
    var = ir.GlobalVariable(module, t2, nameVar)
    var.linkage = "common"
    var.initializer = ir.Constant(t2, None)
    var.align = 4
    list_vars_global.update({nameVar:[typeVar,var]})
    

def mountGlobalArray(node):
    typeVar = ir.IntType(32) if node.parent.children[0].name == 'inteiro' else ir.FloatType()
    nameVar = node.children[0].name
    for i in node.children:
        if i.name == 'indice':
            dimensao = int(len(i.children)/3)
            if dimensao > 1:
                dim_size = list()
                for j in i.children:
                    if j.name in ['NUM_INTEIRO','NUM_PONTO_FLUTUANTE']:
                        size = j.children[0].name
                        dim_size.append(int(size))
                criarVarGlobalArray2D(typeVar, nameVar,dim_size)
                dim_size.clear()
            else:
                if i.children[1].name in ['NUM_INTEIRO','NUM_PONTO_FLUTUANTE']:
                    size = i.children[1].children[0].name
                criarVarGlobalArray(typeVar,nameVar,int(size))
                            

def func_declaracao_varGlobal(node):
    typeVar = ir.IntType(32) if node.children[0].name == 'inteiro' else ir.FloatType()
    if node.children[2].name == 'lista_variaveis':
        for i in node.children[2].children:
            nameVar = i.name
            if nameVar == 'var':
                mountGlobalArray(i)
            else:
                criarVarGlobal(node, typeVar, nameVar)
    elif node.children[2].name == 'var': #variavel array
        mountGlobalArray(node.children[2])
    else: #variavel normal
        nameVar = node.children[2].name
        criarVarGlobal(node, typeVar, nameVar)
   


map_func_especial = {
    'se': func_se,
    'leia': func_leia,
    'escreva': func_escreva,
    'repita': func_repita,
    'retorna': func_retorna,
    'chamada_funcao': func_call_f,
    'atribuicao': func_atribuicao,
    'declaracao_variaveis': func_declaracao_var
}


def buildFuncao(node,nome,tipo_retorno):
    global current_scope
    global retorno_func
    global module
    current_scope = nome
    nome = 'main' if nome == 'principal' else nome
    list_var_local[current_scope] = {'':None}
    list_func_params = list()
    list_func_args_name = list()
    
    for j in node.children:
        if j.name == 'lista_parametros':
            for k in j.children:
                param_tipo = ir.IntType(32) if k.children[0].name == 'inteiro' else ir.FloatType()
                param_name = k.children[2].name
                list_func_params.append(param_tipo)
                list_func_args_name.append(param_name)
                
        elif j.name == 'parametro':
            param_tipo = ir.IntType(32) if j.children[0].name == 'inteiro' else ir.FloatType()
            param_name = j.children[2].name
            list_func_params.append(param_tipo)
            list_func_args_name.append(param_name)
                
                
        if j.name == 'corpo':
            retorno_func = None
            
            tipo_func = ir.FunctionType(tipo_retorno,list_func_params.copy())
            func = ir.Function(module,tipo_func,nome)
            
            if len(list_func_args_name) > 0:
                for i in range(len(list_func_args_name)):
                    func.args[i].name = list_func_args_name[i]
            
            entryBlock = func.append_basic_block('entry')
            exitBasicBlock = func.append_basic_block('exit')
            builder = ir.IRBuilder(entryBlock)
                
            list_func_declarada.update({nome:[func,tipo_retorno,list_func_params,list_func_args_name]})
            
            for k in j.children:
                map_func_especial.get(k.name)(k,builder)
            
            builder.branch(exitBasicBlock)
            builder.position_at_end(exitBasicBlock)
            
            if retorno_func != None:
                builder.ret(retorno_func)
            else:
                builder.ret_void()
            
            
            

def gerarFuncaoVazia(node):
    nome = node.children[0].name
    tipo_retorno = ir.VoidType()
    buildFuncao(node,nome,tipo_retorno)


def gerarFuncao(node):
    global module
    tipo_retorno = ir.IntType(32) if node.children[0].name == 'inteiro' else ir.FloatType()

    for i in node.children:
        if i.name == 'cabecalho':
            nome = i.children[0].name
            buildFuncao(i,nome,tipo_retorno)

                    
if __name__ == '__main__':
    # global module
    arvore = None
    try:
        arvore = semantica.main()
        percorre(arvore)
        montar(arvore.children[0]) #lista_declaracoes

    except:
        print("ERROR: não foi possível gerar o código")


    arquivo = open('meu_modulo.ll', 'w')
    arquivo.write(str(module))
    arquivo.close()
    # print(module)
