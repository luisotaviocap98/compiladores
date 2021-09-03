	.text
	.file	"meu_modulo.ll"
	.globl	main                    # -- Begin function main
	.p2align	4, 0x90
	.type	main,@function
main:                                   # @main
	.cfi_startproc
# %bb.0:                                # %entry
	pushq	%rax
	.cfi_def_cfa_offset 16
	movl	$0, 4(%rsp)
	xorps	%xmm0, %xmm0
	movss	%xmm0, (%rsp)
	callq	leiaInteiro
	movl	%eax, 4(%rsp)
	callq	leiaFlutuante
	movss	%xmm0, (%rsp)
	movl	4(%rsp), %edi
	callq	escrevaInteiro
	movss	(%rsp), %xmm0           # xmm0 = mem[0],zero,zero,zero
	callq	escrevaFlutuante
# %bb.1:                                # %exit
	xorl	%eax, %eax
	popq	%rcx
	.cfi_def_cfa_offset 8
	retq
.Lfunc_end0:
	.size	main, .Lfunc_end0-main
	.cfi_endproc
                                        # -- End function
	.section	".note.GNU-stack","",@progbits
	.addrsig
	.addrsig_sym escrevaInteiro
	.addrsig_sym escrevaFlutuante
	.addrsig_sym leiaInteiro
	.addrsig_sym leiaFlutuante
