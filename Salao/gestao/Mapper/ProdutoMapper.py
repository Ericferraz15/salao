from ..models import Produtos
from ..DTOs.ProdutosDTO import ProdutoRequestDTO, ProdutoResponseDTO

class ProdutoMapper:
    @staticmethod
    def to_entity(dto: ProdutoRequestDTO) -> Produtos:
        return Produtos(
            nome=dto.nome,
            descricao=dto.descricao,
            preco=dto.preco,
            quantidade_estoque=dto.quantidade_estoque,
            estoque_minimo=dto.estoque_minimo
        )

    @staticmethod
    def to_dto(entity: Produtos) -> ProdutoResponseDTO:
        estoque_baixo = entity.quantidade_estoque <= entity.estoque_minimo
        alerta_cor = "vermelho" if estoque_baixo else "verde"

        return ProdutoResponseDTO(
            id=entity.pk,
            nome=entity.nome,
            descricao=entity.descricao,
            preco=entity.preco,
            quantidade_estoque=entity.quantidade_estoque,
            estoque_baixo=estoque_baixo,
            alerta_cor=alerta_cor
        )
