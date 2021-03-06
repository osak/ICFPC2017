package json.comm;

import json.game.Move;
import org.codehaus.jackson.JsonNode;
import org.codehaus.jackson.annotate.JsonIgnore;

public class GameplayResponse {
    public Move.Claim claim;
    public Move.Pass pass;
    public Move.Splurge splurge;
    public Move.Option option;
    public JsonNode state;

    @JsonIgnore
    public Move toMove() {
        if (claim != null) {
            return Move.of(claim);
        } else if (splurge != null) {
            return Move.of(splurge);
        } else if (option != null) {
            return Move.of(option);
        } else {
            return Move.of(pass);
        }
    }
}
